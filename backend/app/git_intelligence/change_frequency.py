from collections import defaultdict
from datetime import datetime
from pathlib import Path

from backend.app.git_intelligence.git_log_analyzer import (
    FIELD_SEPARATOR,
    RECORD_SEPARATOR,
    _is_git_repo,
    _normalize_path,
    _run_git,
)
from backend.app.schemas.git_intelligence import FileChangeFrequency


def calculate_change_frequency(repo_path: str | Path) -> list[FileChangeFrequency]:
    root = Path(repo_path)
    if not _is_git_repo(root):
        return []

    result = _run_git(
        root,
        [
            "log",
            f"--pretty=format:{RECORD_SEPARATOR}%H{FIELD_SEPARATOR}%aI",
            "--name-only",
        ],
    )
    if result is None:
        return []
    return _parse_frequency(result)


def _parse_frequency(output: str) -> list[FileChangeFrequency]:
    counts: dict[str, int] = defaultdict(int)
    last_commit: dict[str, str] = {}
    last_modified_at: dict[str, datetime] = {}

    for raw_block in output.split(RECORD_SEPARATOR):
        block = raw_block.strip()
        if not block:
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        fields = lines[0].split(FIELD_SEPARATOR)
        if len(fields) != 2:
            continue
        commit_hash, committed_at = fields
        parsed_time = datetime.fromisoformat(committed_at)
        for raw_path in lines[1:]:
            file_path = _normalize_path(raw_path)
            counts[file_path] += 1
            if file_path not in last_commit:
                last_commit[file_path] = commit_hash
                last_modified_at[file_path] = parsed_time

    return [
        FileChangeFrequency(
            file_path=file_path,
            commit_count=commit_count,
            last_modified_commit=last_commit.get(file_path),
            last_modified_at=last_modified_at.get(file_path),
        )
        for file_path, commit_count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
