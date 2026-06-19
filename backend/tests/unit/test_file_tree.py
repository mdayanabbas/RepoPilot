from pathlib import Path

import pytest

from backend.app.core.errors import ScanError
from backend.app.scanner.file_tree import scan_file_tree
from backend.app.scanner.service import ScannerService
from backend.app.schemas.scan import FileType


def _write_file(path: Path, content: str = "content\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def test_scan_file_tree_returns_relative_paths_types_and_sizes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_file(repo / "main.py", "print('hello')\n")
    _write_file(repo / "tests" / "test_main.py", "def test_ok(): pass\n")
    _write_file(repo / "pyproject.toml", "[project]\n")
    _write_file(repo / "README.md", "# Repo\n")
    _write_file(repo / "settings.json", "{}\n")
    _write_file(repo / "docker-compose.yml", "services: {}\n")
    _write_file(repo / ".env", "APP_ENV=test\n")
    _write_file(repo / "notes.txt", "notes\n")
    _write_file(repo / "binary.bin", "unknown\n")

    result = scan_file_tree(repo)

    files_by_path = {scanned_file.path: scanned_file for scanned_file in result.files}
    assert set(files_by_path) == {
        ".env",
        "README.md",
        "binary.bin",
        "docker-compose.yml",
        "main.py",
        "notes.txt",
        "pyproject.toml",
        "settings.json",
        "tests/test_main.py",
    }
    assert files_by_path["main.py"].file_type == FileType.python
    assert files_by_path["tests/test_main.py"].file_type == FileType.test
    assert files_by_path["main.py"].size_bytes == len("print('hello')\n")


def test_scan_file_tree_skips_ignored_directories_and_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_file(repo / "app.py")
    _write_file(repo / ".git" / "config")
    _write_file(repo / "node_modules" / "package.json")
    _write_file(repo / "venv" / "lib.py")
    _write_file(repo / "env" / "lib.py")
    _write_file(repo / ".venv" / "lib.py")
    _write_file(repo / "__pycache__" / "main.pyc")
    _write_file(repo / "dist" / "bundle.js")
    _write_file(repo / "build" / "artifact.txt")
    _write_file(repo / ".pytest_cache" / "cache")
    _write_file(repo / ".mypy_cache" / "cache")
    _write_file(repo / ".ruff_cache" / "cache")
    _write_file(repo / ".idea" / "workspace.xml")
    _write_file(repo / ".vscode" / "settings.json")
    _write_file(repo / ".DS_Store")
    _write_file(repo / "thumbs.db")
    _write_file(repo / "main.pyc")
    _write_file(repo / "main.pyo")
    _write_file(repo / "app.log")

    result = scan_file_tree(repo)

    assert [scanned_file.path for scanned_file in result.files] == ["app.py"]


def test_scan_file_tree_returns_counts_for_each_file_type(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_file(repo / "main.py")
    _write_file(repo / "test_main.py")
    _write_file(repo / "pyproject.toml")
    _write_file(repo / "README.md")
    _write_file(repo / "settings.json")
    _write_file(repo / "config.yaml")
    _write_file(repo / ".env")
    _write_file(repo / "notes.txt")
    _write_file(repo / "archive.zip")

    result = ScannerService().scan_repository(repo)

    assert result.total_files == 9
    assert result.python_files == 1
    assert result.test_files == 1
    assert result.config_files == 1
    assert result.markdown_files == 1
    assert result.json_files == 1
    assert result.yaml_files == 1
    assert result.env_files == 1
    assert result.text_files == 1
    assert result.unknown_files == 1


def test_scan_file_tree_raises_scan_error_when_path_does_not_exist(tmp_path: Path) -> None:
    with pytest.raises(ScanError):
        scan_file_tree(tmp_path / "missing")


def test_scan_file_tree_raises_scan_error_when_path_is_not_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "repo.py"
    file_path.write_text("print('not a repo')\n", encoding="utf-8")

    with pytest.raises(ScanError):
        scan_file_tree(file_path)
