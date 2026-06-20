from fnmatch import fnmatch
from pathlib import Path

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "venv",
    "env",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
}

IGNORED_FILES = {
    ".DS_Store",
    "thumbs.db",
}

IGNORED_FILE_PATTERNS = {
    "*.pyc",
    "*.pyo",
    "*.log",
}


def is_ignored_directory(path: str | Path) -> bool:
    return Path(path).name in IGNORED_DIRECTORIES


def is_ignored_file(path: str | Path) -> bool:
    file_name = Path(path).name
    normalized_name = file_name.lower()

    if file_name in IGNORED_FILES or normalized_name in IGNORED_FILES:
        return True

    return any(fnmatch(normalized_name, pattern) for pattern in IGNORED_FILE_PATTERNS)


def should_ignore_path(path: str | Path) -> bool:
    candidate = Path(path)
    if candidate.is_dir():
        return is_ignored_directory(candidate)
    return is_ignored_file(candidate)
