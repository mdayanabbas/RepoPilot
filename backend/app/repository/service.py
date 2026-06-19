import shutil
from pathlib import Path

from backend.app.core.errors import RepositoryError
from backend.app.repository.cleanup import remove_directory
from backend.app.repository.git_client import clone_repository
from backend.app.repository.metadata import build_repository_metadata
from backend.app.repository.workspace import create_workspace
from backend.app.schemas.repository import (
    LoadRepositoryRequest,
    RepositoryMetadata,
    RepositorySourceType,
)
from backend.app.settings import Settings

IGNORED_DIRECTORIES = {".git", "node_modules", "venv", ".venv", "__pycache__"}


class RepositoryService:
    def __init__(self, workspace_root: str | Path | None = None) -> None:
        settings = Settings()
        self.workspace_root = Path(workspace_root or settings.WORKSPACE_ROOT)

    def load_repository(self, request: LoadRepositoryRequest) -> RepositoryMetadata:
        if request.source_type == RepositorySourceType.local:
            return self._load_local_repository(request)
        if request.source_type == RepositorySourceType.git:
            return self._load_git_repository(request)

        raise RepositoryError(
            "Unsupported repository source type",
            details={"source_type": str(request.source_type)},
        )

    def _load_local_repository(self, request: LoadRepositoryRequest) -> RepositoryMetadata:
        source_path = Path(request.source).expanduser().resolve()
        if not source_path.exists():
            raise RepositoryError(
                "Local repository path does not exist",
                details={"source": request.source},
            )
        if not source_path.is_dir():
            raise RepositoryError(
                "Local repository path must be a directory",
                details={"source": request.source},
            )

        workspace_path = create_workspace(self.workspace_root)
        try:
            self._copy_repository(source_path, workspace_path)
        except Exception:
            remove_directory(workspace_path)
            raise

        return build_repository_metadata(
            workspace_id=workspace_path.name,
            repo_name=source_path.name,
            source_type=request.source_type,
            source=request.source,
            local_path=workspace_path,
            branch=request.branch,
        )

    def _load_git_repository(self, request: LoadRepositoryRequest) -> RepositoryMetadata:
        workspace_path = create_workspace(self.workspace_root)
        try:
            clone_repository(request.source, workspace_path, branch=request.branch)
        except Exception:
            remove_directory(workspace_path)
            raise

        repo_name = Path(request.source.rstrip("/")).stem or workspace_path.name
        return build_repository_metadata(
            workspace_id=workspace_path.name,
            repo_name=repo_name,
            source_type=request.source_type,
            source=request.source,
            local_path=workspace_path,
            branch=request.branch,
        )

    def _copy_repository(self, source_path: Path, destination_path: Path) -> None:
        for item in source_path.iterdir():
            destination = destination_path / item.name
            if item.is_dir():
                if item.name in IGNORED_DIRECTORIES:
                    continue
                shutil.copytree(
                    item,
                    destination,
                    ignore=shutil.ignore_patterns(*IGNORED_DIRECTORIES),
                )
            else:
                shutil.copy2(item, destination)
