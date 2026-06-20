from pathlib import Path

from backend.app.scanner.file_tree import scan_file_tree
from backend.app.scanner.framework_detector import detect_framework
from backend.app.schemas.framework import SupportedFramework


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_detects_fastapi_repository(tmp_path: Path) -> None:
    repo = tmp_path / "fastapi_repo"
    _write_file(repo / "requirements.txt", "fastapi==0.110.0\nuvicorn\n")
    _write_file(
        repo / "main.py",
        "from fastapi import FastAPI\n\napp = FastAPI()\n",
    )

    scan_result = scan_file_tree(repo)
    result = detect_framework(repo, scan_result)

    assert result.framework == SupportedFramework.fastapi
    assert result.confidence > 0.5
    assert result.signals
    assert {signal.source for signal in result.signals} == {"requirements.txt", "main.py"}


def test_detects_flask_repository(tmp_path: Path) -> None:
    repo = tmp_path / "flask_repo"
    _write_file(
        repo / "pyproject.toml",
        '[project]\ndependencies = ["flask>=3.0"]\n',
    )
    _write_file(
        repo / "app.py",
        "from flask import Flask\n\napp = Flask(__name__)\n",
    )

    scan_result = scan_file_tree(repo)
    result = detect_framework(repo, scan_result)

    assert result.framework == SupportedFramework.flask
    assert result.confidence > 0.5
    assert result.signals
    assert {signal.source for signal in result.signals} == {"pyproject.toml", "app.py"}


def test_returns_unknown_for_repository_without_framework_signals(tmp_path: Path) -> None:
    repo = tmp_path / "unknown_repo"
    _write_file(repo / "requirements.txt", "requests==2.32.0\n")
    _write_file(repo / "main.py", "def handler():\n    return 'ok'\n")
    _write_file(repo / "README.md", "# Unknown\n")

    scan_result = scan_file_tree(repo)
    result = detect_framework(repo, scan_result)

    assert result.framework == SupportedFramework.unknown
    assert result.confidence < 0.2
    assert result.signals == []
