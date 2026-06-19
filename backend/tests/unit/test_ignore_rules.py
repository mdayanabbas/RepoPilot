from pathlib import Path

from backend.app.scanner.ignore_rules import (
    is_ignored_directory,
    is_ignored_file,
    should_ignore_path,
)


def test_ignored_directories_are_detected() -> None:
    ignored_directories = [
        ".git",
        "node_modules",
        "venv",
        "env",
        ".venv",
        "__pycache__",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".idea",
        ".vscode",
    ]

    for directory in ignored_directories:
        assert is_ignored_directory(directory) is True


def test_non_ignored_directory_is_not_detected() -> None:
    assert is_ignored_directory("app") is False
    assert is_ignored_directory("tests") is False


def test_ignored_files_are_detected() -> None:
    ignored_files = [
        ".DS_Store",
        "thumbs.db",
        "module.pyc",
        "module.pyo",
        "server.log",
    ]

    for file_name in ignored_files:
        assert is_ignored_file(file_name) is True


def test_non_ignored_file_is_not_detected() -> None:
    assert is_ignored_file("main.py") is False
    assert is_ignored_file("README.md") is False


def test_should_ignore_path_handles_files_and_directories(tmp_path: Path) -> None:
    ignored_directory = tmp_path / ".git"
    ignored_directory.mkdir()
    ignored_file = tmp_path / "debug.log"
    ignored_file.write_text("log\n", encoding="utf-8")
    included_file = tmp_path / "main.py"
    included_file.write_text("print('ok')\n", encoding="utf-8")

    assert should_ignore_path(ignored_directory) is True
    assert should_ignore_path(ignored_file) is True
    assert should_ignore_path(included_file) is False
