from pathlib import Path

from backend.app.schemas.repository import RepositoryMetadata, RepositorySourceType


def count_files(path: str | Path) -> int:
    root = Path(path)
    return sum(1 for item in root.rglob("*") if item.is_file())


def build_repository_metadata(
    *,
    workspace_id: str,
    repo_name: str,
    source_type: RepositorySourceType,
    source: str,
    local_path: str | Path,
    branch: str | None,
) -> RepositoryMetadata:
    local_path_string = str(Path(local_path))
    return RepositoryMetadata(
        workspace_id=workspace_id,
        repo_name=repo_name,
        source_type=source_type.value,
        source=source,
        local_path=local_path_string,
        branch=branch,
        total_files=count_files(local_path_string),
    )
