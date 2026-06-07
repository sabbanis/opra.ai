"""Public repository hygiene checks for external OPRA repositories."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


TEXT_EXTENSIONS = {
    "",
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}

SELF_PATHS = {
    Path("tools/public_repo_hygiene.py"),
    Path("tests/unit/test_public_repo_hygiene.py"),
}


@dataclass(frozen=True)
class HygieneRule:
    name: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class HygieneFinding:
    path: Path
    line_number: int
    rule_name: str
    line: str

    def format(self) -> str:
        return f"{self.path}:{self.line_number}: {self.rule_name}: {self.line.strip()}"


PUBLIC_REPO_RULES = (
    HygieneRule(
        "absolute user home path",
        re.compile(r"(?:/Users|/home)/[A-Za-z0-9._-]+/"),
    ),
    HygieneRule(
        "private sibling repository path",
        re.compile(
            r"(?i)(?:^|[^A-Za-z0-9_./-])(?:\.\./)?company-os/"
            r"(?:\.github|apps|demos|designs|docs|modules|packages|platform|tests)/"
        ),
    ),
    HygieneRule(
        "private Company OS repository URL",
        re.compile(r"https://github\.com/sabbanis/company-os(?:[/?#\s`)]|$)"),
    ),
    HygieneRule(
        "private planning document reference",
        re.compile(
            r"(?i)(?:architecture-decisions|go-to-market-plan|mvp-build-plan|"
            r"proposal-check-smoke-test-report|software-requirements-document)\.md"
        ),
    ),
    HygieneRule(
        "private key material",
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    ),
    HygieneRule(
        "AWS access key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    HygieneRule(
        "GitHub access token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    ),
    HygieneRule(
        "secret assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*"
            r"['\"]?[A-Za-z0-9_./+=-]{16,}"
        ),
    ),
)


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in relative_parts):
            continue
        if path.relative_to(root) in SELF_PATHS:
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield path


def scan_repo(
    root: Path,
    rules: Sequence[HygieneRule] = PUBLIC_REPO_RULES,
) -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []
    for path in iter_text_files(root):
        relative_path = path.relative_to(root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for rule in rules:
                if rule.pattern.search(line):
                    findings.append(
                        HygieneFinding(
                            path=relative_path,
                            line_number=line_number,
                            rule_name=rule.name,
                            line=line,
                        )
                    )
    return findings


def main() -> int:
    root = Path.cwd()
    findings = scan_repo(root)
    if findings:
        for finding in findings:
            print(finding.format())
        return 1
    print("Public repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
