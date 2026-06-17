"""GitHub pull-request backed messaging primitives."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from company_os_core.github import (
    DEFAULT_GITHUB_MESSAGE_THREAD_DIR,
    GitHubAdapter,
    GitHubFileChange,
    GitHubPullRequestCommentResult,
    GitHubPullRequestResult,
    GitHubPublishError,
)
from company_os_core.models import utc_now
from company_os_core.serialization import read_yaml, stable_hash, to_plain_data, to_yaml, write_yaml


MESSAGE_THREAD_MARKER = "<!-- opra-ai-message-thread -->"


@dataclass(frozen=True)
class GitHubMessage:
    """One visible message in a PR-backed conversation."""

    id: str
    author: str
    body: str
    created_at: datetime
    source: str
    url: str = ""


@dataclass(frozen=True)
class GitHubMessageThread:
    """A top-level chat message represented by one GitHub pull request."""

    id: str
    title: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    participants: tuple[str, ...]
    base_branch: str
    branch_name: str
    pull_request: GitHubPullRequestResult
    messages: tuple[GitHubMessage, ...] = field(default_factory=tuple)
    state: str = "open"


@dataclass(frozen=True)
class WrittenGitHubMessageThread:
    """Persisted PR-backed message thread."""

    path: Path
    thread: GitHubMessageThread


class GitHubMessagingService:
    """Create and update Slack-like conversations using GitHub pull requests."""

    def __init__(
        self,
        adapter: GitHubAdapter,
        repo_root: Path,
        thread_dir: Path = DEFAULT_GITHUB_MESSAGE_THREAD_DIR,
    ) -> None:
        self._adapter = adapter
        self._repo_root = repo_root
        self._thread_dir = thread_dir

    def list_threads(self) -> tuple[WrittenGitHubMessageThread, ...]:
        """Read locally saved message thread previews, newest first."""

        root = self._thread_root()
        if not root.exists():
            return ()
        rows = []
        for path in sorted(root.glob("*.yaml"), reverse=True):
            rows.append(
                WrittenGitHubMessageThread(
                    path=path,
                    thread=github_message_thread_from_data(read_yaml(path)),
                )
            )
        return tuple(rows)

    def read_thread(self, thread_id: str) -> WrittenGitHubMessageThread:
        """Read one locally saved message thread preview."""

        path = self.thread_path(thread_id)
        if not path.exists():
            raise FileNotFoundError(f"Message thread not found: {thread_id}")
        return WrittenGitHubMessageThread(
            path=path,
            thread=github_message_thread_from_data(read_yaml(path)),
        )

    def create_thread(
        self,
        title: str,
        body: str,
        author: str,
        participants: tuple[str, ...] = (),
        base_branch: str = "main",
    ) -> WrittenGitHubMessageThread:
        """Create a new PR-backed conversation from one top-level message."""

        clean_title = _required_text("title", title)
        clean_body = _required_text("body", body)
        clean_author = _required_text("author", author)
        clean_base_branch = _required_text("base_branch", base_branch)
        clean_participants = _clean_tuple(participants)
        created_at = utc_now()
        thread_id = _thread_id(
            title=clean_title,
            body=clean_body,
            author=clean_author,
            created_at=created_at,
        )
        branch_name = _thread_branch_name(thread_id)
        file_path = _thread_repo_path(thread_id)

        self._adapter.create_branch(branch_name=branch_name, base_branch=clean_base_branch)
        self._adapter.commit_files(
            branch_name=branch_name,
            message=f"[opra.ai message] {clean_title}",
            files=(
                GitHubFileChange(
                    path=file_path,
                    content=_thread_seed_content(
                        thread_id=thread_id,
                        title=clean_title,
                        body=clean_body,
                        author=clean_author,
                        participants=clean_participants,
                        created_at=created_at,
                    ),
                ),
            ),
        )
        pull_request = self._adapter.open_pull_request(
            branch_name=branch_name,
            base_branch=clean_base_branch,
            title=f"[opra.ai message] {clean_title}",
            body=_thread_pr_body(
                thread_id=thread_id,
                body=clean_body,
                author=clean_author,
                participants=clean_participants,
            ),
        )
        if clean_participants:
            self._adapter.request_pull_request_reviewers(
                number=pull_request.number,
                reviewers=clean_participants,
            )

        initial_message = GitHubMessage(
            id="initial",
            author=clean_author,
            body=clean_body,
            created_at=created_at,
            source="pull_request",
            url=pull_request.url,
        )
        thread = GitHubMessageThread(
            id=thread_id,
            title=clean_title,
            created_by=clean_author,
            created_at=created_at,
            updated_at=created_at,
            participants=clean_participants,
            base_branch=clean_base_branch,
            branch_name=branch_name,
            pull_request=pull_request,
            messages=(initial_message,),
        )
        return self._write_thread(thread)

    def add_comment(
        self,
        thread_id: str,
        body: str,
        author: str,
    ) -> WrittenGitHubMessageThread:
        """Append a reply to an existing PR-backed conversation."""

        written = self.read_thread(thread_id)
        clean_body = _required_text("body", body)
        clean_author = _required_text("author", author)
        comment = self._adapter.create_pull_request_comment(
            number=written.thread.pull_request.number,
            body=clean_body,
        )
        message = _message_from_comment(comment=comment, author=clean_author)
        updated = replace(
            written.thread,
            messages=written.thread.messages + (message,),
            updated_at=message.created_at,
        )
        return self._write_thread(updated)

    def sync_comments(self, thread_id: str) -> WrittenGitHubMessageThread:
        """Refresh saved reply messages from the GitHub pull-request comments."""

        written = self.read_thread(thread_id)
        initial_messages = tuple(
            message for message in written.thread.messages if message.source == "pull_request"
        )
        comments = self._adapter.list_pull_request_comments(written.thread.pull_request.number)
        comment_messages = tuple(
            _message_from_comment(comment=comment, author=comment.author or "github")
            for comment in comments
        )
        messages = initial_messages + comment_messages
        updated_at = messages[-1].created_at if messages else written.thread.updated_at
        return self._write_thread(
            replace(written.thread, messages=messages, updated_at=updated_at)
        )

    def thread_path(self, thread_id: str) -> Path:
        """Return the safe preview path for a thread ID."""

        return self._thread_root() / f"{_safe_file_stem(thread_id)}.yaml"

    def _write_thread(self, thread: GitHubMessageThread) -> WrittenGitHubMessageThread:
        path = self.thread_path(thread.id)
        write_yaml(path, thread)
        return WrittenGitHubMessageThread(path=path, thread=thread)

    def _thread_root(self) -> Path:
        return self._thread_dir if self._thread_dir.is_absolute() else self._repo_root / self._thread_dir


def github_message_thread_from_data(data: Any) -> GitHubMessageThread:
    """Parse a serialized GitHub message thread."""

    if not isinstance(data, Mapping):
        raise GitHubPublishError("GitHub message thread data must contain an object")
    return GitHubMessageThread(
        id=str(data["id"]),
        title=str(data["title"]),
        created_by=str(data["created_by"]),
        created_at=_parse_timestamp(data["created_at"]),
        updated_at=_parse_timestamp(data["updated_at"]),
        participants=_string_tuple(data.get("participants", [])),
        base_branch=str(data["base_branch"]),
        branch_name=str(data["branch_name"]),
        pull_request=_pull_request_from_data(data.get("pull_request", {})),
        messages=_messages_from_data(data.get("messages", [])),
        state=str(data.get("state", "open")),
    )


def _pull_request_from_data(data: Any) -> GitHubPullRequestResult:
    if not isinstance(data, Mapping):
        raise GitHubPublishError("GitHub message thread pull_request must be an object")
    return GitHubPullRequestResult(
        number=int(data["number"]),
        title=str(data["title"]),
        body=str(data.get("body", "")),
        head_branch=str(data["head_branch"]),
        base_branch=str(data["base_branch"]),
        url=str(data.get("url", "")),
    )


def _messages_from_data(data: Any) -> tuple[GitHubMessage, ...]:
    if data is None or data == {}:
        return ()
    if not isinstance(data, list):
        raise GitHubPublishError("GitHub message thread messages must be a list")
    messages = []
    for item in data:
        if not isinstance(item, Mapping):
            raise GitHubPublishError("GitHub message entry must be an object")
        messages.append(
            GitHubMessage(
                id=str(item["id"]),
                author=str(item["author"]),
                body=str(item["body"]),
                created_at=_parse_timestamp(item["created_at"]),
                source=str(item["source"]),
                url=str(item.get("url", "")),
            )
        )
    return tuple(messages)


def _message_from_comment(
    comment: GitHubPullRequestCommentResult,
    author: str,
) -> GitHubMessage:
    created_at = comment.created_at or utc_now()
    message_id = comment.id or "comment_" + stable_hash(
        {
            "body": comment.body,
            "author": comment.author or author,
            "created_at": created_at,
            "url": comment.url,
        }
    )[:12]
    return GitHubMessage(
        id=message_id,
        author=comment.author or author,
        body=comment.body,
        created_at=created_at,
        source="pull_request_comment",
        url=comment.url,
    )


def _thread_id(title: str, body: str, author: str, created_at: datetime) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:36].strip("-")
    if not slug:
        slug = "message"
    digest = stable_hash(
        {
            "title": title,
            "body": body,
            "author": author,
            "created_at": created_at,
        }
    )[:12]
    return f"msg_{slug}_{digest}"


def _thread_branch_name(thread_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9._/-]+", "-", thread_id.strip())
    safe_id = safe_id.replace("..", ".").strip("./-")
    if not safe_id:
        raise GitHubPublishError("message thread id cannot produce a branch name")
    return f"opra-ai/messages/{safe_id}"


def _thread_repo_path(thread_id: str) -> str:
    return f"{DEFAULT_GITHUB_MESSAGE_THREAD_DIR}/{_safe_file_stem(thread_id)}.yaml"


def _thread_seed_content(
    thread_id: str,
    title: str,
    body: str,
    author: str,
    participants: tuple[str, ...],
    created_at: datetime,
) -> str:
    return to_yaml(
        {
            "kind": "opra.ai/github-message-thread",
            "id": thread_id,
            "title": title,
            "author": author,
            "participants": list(participants),
            "created_at": to_plain_data(created_at),
            "initial_message": body,
        }
    )


def _thread_pr_body(
    thread_id: str,
    body: str,
    author: str,
    participants: tuple[str, ...],
) -> str:
    participant_lines = _markdown_list(participants)
    return "\n".join(
        (
            MESSAGE_THREAD_MARKER,
            "## Message",
            "",
            body,
            "",
            "## Routing",
            "",
            f"- Thread: `{thread_id}`",
            f"- Author: `{author}`",
            "- Participants:",
            participant_lines,
        )
    )


def _markdown_list(values: tuple[str, ...]) -> str:
    if not values:
        return "  - None"
    return "\n".join(f"  - {value}" for value in values)


def _required_text(field_name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise GitHubPublishError(f"{field_name} is required")
    return cleaned


def _clean_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return _unique_values(tuple(str(value).strip() for value in values if str(value).strip()))


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None or value == {}:
        return ()
    if isinstance(value, str):
        return _clean_tuple(tuple(value.split(",")))
    if isinstance(value, (list, tuple)):
        return _clean_tuple(tuple(str(item) for item in value))
    raise GitHubPublishError("expected a list of strings")


def _unique_values(values: tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return tuple(unique)


def _safe_file_stem(value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    if not stem:
        raise GitHubPublishError("message thread id is required")
    return stem


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
