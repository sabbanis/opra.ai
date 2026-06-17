"""GitHub pull-request backed messaging tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    CommandResult,
    GitHubCLIAdapter,
    GitHubMessageThread,
    GitHubMessagingService,
    GitHubPublishError,
    MockGitHubAdapter,
    github_message_thread_from_data,
)
from company_os_core.serialization import read_yaml


class GitHubMessagingTests(unittest.TestCase):
    def test_create_thread_builds_branch_pull_request_and_preview(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adapter = MockGitHubAdapter(repo_url="https://github.com/acme/opra.ai")
            service = GitHubMessagingService(adapter=adapter, repo_root=root)

            written = service.create_thread(
                title="Launch room",
                body="Coordinate the launch checklist.",
                author="owner",
                participants=("@sabbanis", "octocat", "@sabbanis"),
                base_branch="main",
            )

            self.assertTrue(written.path.exists())
            self.assertTrue(written.thread.id.startswith("msg_launch-room_"))
            self.assertEqual(written.thread.title, "Launch room")
            self.assertEqual(written.thread.messages[0].body, "Coordinate the launch checklist.")
            self.assertEqual(written.thread.participants, ("@sabbanis", "octocat"))
            self.assertEqual(adapter.branches[written.thread.branch_name], "main")
            self.assertEqual(adapter.pull_requests[0].number, 1)
            self.assertEqual(adapter.pull_request_reviewers[1], ("@sabbanis", "octocat"))
            self.assertEqual(
                adapter.commits[0].file_paths,
                (f"platform/integrations/github/message_threads/{written.thread.id}.yaml",),
            )

            saved = github_message_thread_from_data(read_yaml(written.path))
            self.assertEqual(saved.id, written.thread.id)
            self.assertEqual(saved.pull_request.url, "https://github.com/acme/opra.ai/pull/1")

    def test_add_comment_appends_pull_request_comment_message(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adapter = MockGitHubAdapter(repo_url="https://github.com/acme/opra.ai")
            service = GitHubMessagingService(adapter=adapter, repo_root=root)
            created = service.create_thread(
                title="Support handoff",
                body="Need help on the Acme incident.",
                author="support_engineer",
                participants=("engineering-lead",),
            )

            replied = service.add_comment(
                thread_id=created.thread.id,
                body="I can take the next investigation step.",
                author="engineering_lead",
            )

            self.assertEqual(len(replied.thread.messages), 2)
            self.assertEqual(replied.thread.messages[1].author, "engineering_lead")
            self.assertEqual(replied.thread.messages[1].source, "pull_request_comment")
            self.assertEqual(replied.thread.messages[1].id, "1")
            self.assertIn("#issuecomment-1", replied.thread.messages[1].url)
            self.assertEqual(
                read_yaml(replied.path)["messages"][1]["body"],
                "I can take the next investigation step.",
            )

    def test_list_threads_returns_newest_saved_previews_first(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adapter = MockGitHubAdapter(repo_url="https://github.com/acme/opra.ai")
            service = GitHubMessagingService(adapter=adapter, repo_root=root)
            first = service.create_thread("First", "One", "owner")
            second = service.create_thread("Second", "Two", "owner")

            listed = service.list_threads()

            self.assertEqual([item.thread.id for item in listed], [second.thread.id, first.thread.id])

    def test_cli_adapter_runs_pr_participant_and_comment_commands(self) -> None:
        with TemporaryDirectory() as temp_dir:
            runner = MessagingRecordingRunner()
            adapter = GitHubCLIAdapter(repo_root=Path(temp_dir), runner=runner)

            adapter.request_pull_request_reviewers(42, ("@sabbanis", "octocat"))
            comment = adapter.create_pull_request_comment(42, "Reply from the room.")
            comments = adapter.list_pull_request_comments(42)

            self.assertEqual(comment.id, "123")
            self.assertEqual(comments[0].author, "octocat")
            self.assertEqual(comments[0].body, "Reply from the room.")
            commands = tuple(call.args for call in runner.calls)
            self.assertIn(("gh", "pr", "edit", "42", "--add-reviewer", "@sabbanis"), commands)
            self.assertIn(("gh", "pr", "edit", "42", "--add-reviewer", "octocat"), commands)
            self.assertIn(
                ("gh", "pr", "comment", "42", "--body", "Reply from the room."),
                commands,
            )
            self.assertIn(("gh", "pr", "view", "42", "--json", "comments"), commands)

    def test_thread_parser_rejects_invalid_payload(self) -> None:
        with self.assertRaises(GitHubPublishError):
            github_message_thread_from_data([])


class MessagingRecordingRunner:
    """Fake command runner for GitHub CLI messaging adapter tests."""

    def __init__(self) -> None:
        self.calls: list[CommandResult] = []

    def run(self, args, cwd: Path, check: bool = True) -> CommandResult:
        command = tuple(args)
        result = self._result(command)
        self.calls.append(result)
        if check and result.returncode != 0:
            raise GitHubPublishError(result.stderr or result.stdout or "command failed")
        return result

    def _result(self, command: tuple[str, ...]) -> CommandResult:
        if command[:3] == ("gh", "pr", "comment"):
            return CommandResult(
                args=command,
                returncode=0,
                stdout="https://github.com/acme/opra.ai/pull/42#issuecomment-123\n",
            )
        if command[:3] == ("gh", "pr", "view"):
            return CommandResult(
                args=command,
                returncode=0,
                stdout=(
                    '{"comments": [{"id": "C_123", "body": "Reply from the room.", '
                    '"author": {"login": "octocat"}, '
                    '"createdAt": "2026-06-17T12:00:00Z", '
                    '"updatedAt": "2026-06-17T12:00:00Z", '
                    '"url": "https://github.com/acme/opra.ai/pull/42#issuecomment-123"}]}'
                ),
            )
        return CommandResult(args=command, returncode=0)


if __name__ == "__main__":
    unittest.main()
