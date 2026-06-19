import shutil
from pathlib import Path


def remove_directory(path: str | Path) -> None:
    directory = Path(path)
    if directory.exists():
        shutil.rmtree(directory)
