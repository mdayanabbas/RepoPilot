import re
import shutil
from pathlib import Path
from uuid import uuid4

WORKSPACE_ID_PATTERN = re.compile(r"^repo_[a-f0-9]{32}$")


def create_workspace_id() -> str:
    return f"repo_{uuid4().hex}"


def is_safe_workspace_id(workspace_id: str) -> bool:
    if not workspace_id:
        return False
    if "/" in workspace_id or "\\" in workspace_id or ".." in workspace_id:
        return False
    if Path(workspace_id).is_absolute():
        return False
    return WORKSPACE_ID_PATTERN.fullmatch(workspace_id) is not None


def ensure_workspace_root(workspace_root: str | Path) -> Path:
    root = Path(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_workspace(workspace_root: str | Path, workspace_id: str | None = None) -> Path:
    root = ensure_workspace_root(workspace_root)
    safe_workspace_id = workspace_id or create_workspace_id()

    if not is_safe_workspace_id(safe_workspace_id):
        raise ValueError(f"Unsafe workspace id: {safe_workspace_id}")

    workspace_path = root / safe_workspace_id
    workspace_path.mkdir(parents=False, exist_ok=False)
    return workspace_path


def delete_workspace(workspace_root: str | Path, workspace_id: str) -> None:
    if not is_safe_workspace_id(workspace_id):
        raise ValueError(f"Unsafe workspace id: {workspace_id}")

    workspace_path = Path(workspace_root) / workspace_id
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
