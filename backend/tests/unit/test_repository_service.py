from pathlib import Path
from uuid import UUID

import pytest

from backend.app.core.errors import RepositoryError
from backend.app.repository.service import RepositoryService
from backend.app.schemas.repository import LoadRepositoryRequest, RepositorySourceType


def _create_local_repository(path: Path) -> None:
    path.mkdir()
    (path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (path / "README.md").write_text("# Sample\n", encoding="utf-8")

    for folder_name in [".git", "node_modules", "venv", ".venv", "__pycache__"]:
        ignored_folder = path / folder_name
        ignored_folder.mkdir()
        (ignored_folder / "ignored.txt").write_text("ignored\n", encoding="utf-8")

    package = path / "app"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "routes.py").write_text("def route(): pass\n", encoding="utf-8")


def test_load_local_repository_from_tmp_path(tmp_path: Path) -> None:
    source_repo = tmp_path / "sample-api"
    workspace_root = tmp_path / "storage" / "workspaces"
    _create_local_repository(source_repo)

    service = RepositoryService(workspace_root=workspace_root)
    metadata = service.load_repository(
        LoadRepositoryRequest(
            source_type=RepositorySourceType.local,
            source=str(source_repo),
            branch="main",
        )
    )

    assert metadata.repo_name == "sample-api"
    assert metadata.source_type == "local"
    assert metadata.source == str(source_repo)
    assert metadata.branch == "main"
    assert metadata.workspace_id.startswith("repo_")
    UUID(metadata.workspace_id.removeprefix("repo_"))


def test_local_repository_is_copied_into_workspace(tmp_path: Path) -> None:
    source_repo = tmp_path / "sample-api"
    workspace_root = tmp_path / "storage" / "workspaces"
    _create_local_repository(source_repo)

    metadata = RepositoryService(workspace_root=workspace_root).load_repository(
        LoadRepositoryRequest(source_type="local", source=str(source_repo))
    )

    workspace_path = Path(metadata.local_path)
    assert workspace_path == workspace_root / metadata.workspace_id
    assert (workspace_path / "main.py").exists()
    assert (workspace_path / "app" / "routes.py").exists()


def test_original_local_repository_remains_untouched(tmp_path: Path) -> None:
    source_repo = tmp_path / "sample-api"
    workspace_root = tmp_path / "storage" / "workspaces"
    _create_local_repository(source_repo)

    RepositoryService(workspace_root=workspace_root).load_repository(
        LoadRepositoryRequest(source_type="local", source=str(source_repo))
    )

    assert (source_repo / "main.py").read_text(encoding="utf-8") == "print('hello')\n"
    assert (source_repo / ".git" / "ignored.txt").exists()


def test_ignored_folders_are_not_copied(tmp_path: Path) -> None:
    source_repo = tmp_path / "sample-api"
    workspace_root = tmp_path / "storage" / "workspaces"
    _create_local_repository(source_repo)

    metadata = RepositoryService(workspace_root=workspace_root).load_repository(
        LoadRepositoryRequest(source_type="local", source=str(source_repo))
    )

    workspace_path = Path(metadata.local_path)
    for folder_name in [".git", "node_modules", "venv", ".venv", "__pycache__"]:
        assert not (workspace_path / folder_name).exists()


def test_metadata_contains_expected_values(tmp_path: Path) -> None:
    source_repo = tmp_path / "sample-api"
    workspace_root = tmp_path / "storage" / "workspaces"
    _create_local_repository(source_repo)

    metadata = RepositoryService(workspace_root=workspace_root).load_repository(
        LoadRepositoryRequest(
            source_type="local",
            source=str(source_repo),
            branch=None,
        )
    )

    assert metadata.workspace_id
    assert metadata.repo_name == "sample-api"
    assert metadata.source_type == "local"
    assert metadata.source == str(source_repo)
    assert metadata.local_path == str(workspace_root / metadata.workspace_id)
    assert metadata.branch is None
    assert metadata.total_files == 4


def test_invalid_local_path_raises_repository_error(tmp_path: Path) -> None:
    service = RepositoryService(workspace_root=tmp_path / "workspaces")

    with pytest.raises(RepositoryError):
        service.load_repository(
            LoadRepositoryRequest(source_type="local", source=str(tmp_path / "missing"))
        )


def test_source_path_that_is_file_raises_repository_error(tmp_path: Path) -> None:
    source_file = tmp_path / "repo.py"
    source_file.write_text("print('not a directory')\n", encoding="utf-8")
    service = RepositoryService(workspace_root=tmp_path / "workspaces")

    with pytest.raises(RepositoryError):
        service.load_repository(
            LoadRepositoryRequest(source_type="local", source=str(source_file))
        )
