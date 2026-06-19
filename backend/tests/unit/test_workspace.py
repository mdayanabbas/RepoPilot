from pathlib import Path

from backend.app.repository.workspace import (
    create_workspace,
    create_workspace_id,
    delete_workspace,
    ensure_workspace_root,
    is_safe_workspace_id,
)


def test_create_workspace_id_returns_repo_prefixed_string() -> None:
    workspace_id = create_workspace_id()

    assert isinstance(workspace_id, str)
    assert workspace_id.startswith("repo_")


def test_create_workspace_id_returns_unique_ids() -> None:
    first_workspace_id = create_workspace_id()
    second_workspace_id = create_workspace_id()

    assert first_workspace_id != second_workspace_id


def test_is_safe_workspace_id_accepts_valid_repo_ids() -> None:
    assert is_safe_workspace_id(create_workspace_id()) is True


def test_is_safe_workspace_id_rejects_unsafe_values() -> None:
    unsafe_values = [
        "../abc",
        "repo/abc",
        "repo\\abc",
        "C:\\temp\\repo",
        "/tmp/repo",
        "",
    ]

    for value in unsafe_values:
        assert is_safe_workspace_id(value) is False


def test_ensure_workspace_root_creates_workspace_root(tmp_path: Path) -> None:
    workspace_root = tmp_path / "storage" / "workspaces"

    result = ensure_workspace_root(workspace_root)

    assert result == workspace_root
    assert workspace_root.exists()
    assert workspace_root.is_dir()


def test_create_workspace_creates_workspace_directory(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    workspace_id = create_workspace_id()

    workspace_path = create_workspace(workspace_root, workspace_id)

    assert workspace_path == workspace_root / workspace_id
    assert workspace_path.exists()
    assert workspace_path.is_dir()


def test_delete_workspace_removes_workspace_directory(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    workspace_id = create_workspace_id()
    workspace_path = create_workspace(workspace_root, workspace_id)

    delete_workspace(workspace_root, workspace_id)

    assert not workspace_path.exists()
