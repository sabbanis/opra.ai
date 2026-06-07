"""Project-level constants and repository checks."""

from pathlib import Path

PRODUCT_NAME = "opra.ai"

REQUIRED_TOP_LEVEL_PATHS = (
    "modules",
    "platform",
    "apps",
    "packages",
    "demos",
    "docs",
    "tests",
    ".github/workflows",
)


def missing_required_paths(repo_root: Path) -> tuple[str, ...]:
    """Return required top-level paths missing from an opra.ai checkout."""

    return tuple(
        relative_path
        for relative_path in REQUIRED_TOP_LEVEL_PATHS
        if not (repo_root / relative_path).exists()
    )
