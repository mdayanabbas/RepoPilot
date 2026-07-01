from datetime import datetime, timezone
from pathlib import Path

from backend.app.git_intelligence.git_log_analyzer import (
    _is_git_repo,
    _normalize_path,
    _run_git,
)
from backend.app.schemas.git_intelligence import GitBlameLine


def get_file_blame(repo_path: str | Path, file_path: str | None) -> list[GitBlameLine]:
    if not file_path:
        return []
    root = Path(repo_path)
    if not _is_git_repo(root):
        return []
    normalized_path = _normalize_path(file_path)
    if not (root / normalized_path).is_file():
        return []

    result = _run_git(root, ["blame", "--line-porcelain", "--", normalized_path])
    if result is None:
        return []
    return _parse_blame(normalized_path, result)


def _parse_blame(file_path: str, output: str) -> list[GitBlameLine]:
    blame_lines: list[GitBlameLine] = []
    current_commit = ""
    current_author = ""
    current_time: datetime | None = None
    line_number = 0

    for line in output.splitlines():
        if _starts_blame_header(line):
            current_commit = line.split()[0]
            continue
        if line.startswith("author "):
            current_author = line.removeprefix("author ")
            continue
        if line.startswith("author-time "):
            raw_timestamp = line.removeprefix("author-time ")
            try:
                current_time = datetime.fromtimestamp(
                    int(raw_timestamp),
                    tz=timezone.utc,
                )
            except ValueError:
                current_time = None
            continue
        if line.startswith("\t"):
            line_number += 1
            if current_commit and current_time is not None:
                blame_lines.append(
                    GitBlameLine(
                        file_path=file_path,
                        line_number=line_number,
                        commit_hash=current_commit,
                        author_name=current_author,
                        committed_at=current_time,
                        line_content=line[1:],
                    )
                )
    return blame_lines


def _starts_blame_header(line: str) -> bool:
    parts = line.split()
    return len(parts) >= 4 and len(parts[0]) >= 7 and _is_hex(parts[0])


def _is_hex(value: str) -> bool:
    return all(character in "0123456789abcdefABCDEF" for character in value)
