from pathlib import Path


def resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def is_path_within(parent: str | Path, child: str | Path) -> bool:
    parent_path = resolve_path(parent)
    child_path = resolve_path(child)

    try:
        child_path.relative_to(parent_path)
    except ValueError:
        return False
    return True
