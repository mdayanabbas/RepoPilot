from datetime import datetime
from pathlib import Path

from backend.app.schemas.git_intelligence import GitCommitInfo

FIELD_SEPARATOR = "\x1f"
RECORD_SEPARATOR = "\x1e"


def get_recent_commits(repo_path: str | Path, limit: int = 20) -> list[GitCommitInfo]:
    root = Path(repo_path)
    if not _is_git_repo(root):
        return []

    result = _run_git(
        root,
        [
            "log",
            "-n",
            str(limit),
            f"--pretty=format:{RECORD_SEPARATOR}%H{FIELD_SEPARATOR}%h"
            f"{FIELD_SEPARATOR}%an{FIELD_SEPARATOR}%ae{FIELD_SEPARATOR}%aI"
            f"{FIELD_SEPARATOR}%s",
            "--name-only",
        ],
    )
    if result is None:
        return []
    return _parse_log(result)


def _parse_log(output: str) -> list[GitCommitInfo]:
    commits: list[GitCommitInfo] = []
    for raw_block in output.split(RECORD_SEPARATOR):
        block = raw_block.strip()
        if not block:
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        fields = lines[0].split(FIELD_SEPARATOR)
        if len(fields) != 6:
            continue
        commit_hash, short_hash, author_name, author_email, committed_at, message = fields
        changed_files = [_normalize_path(line) for line in lines[1:]]
        commits.append(
            GitCommitInfo(
                commit_hash=commit_hash,
                short_hash=short_hash,
                author_name=author_name,
                author_email=author_email,
                committed_at=datetime.fromisoformat(committed_at),
                message=message,
                changed_files=changed_files,
            )
        )
    return commits


def _is_git_repo(root: Path) -> bool:
    return root.is_dir() and (root / ".git").exists()


def _run_git(root: Path, args: list[str]) -> str | None:
    import subprocess

    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _normalize_path(path: str) -> str:
    return Path(path).as_posix()
