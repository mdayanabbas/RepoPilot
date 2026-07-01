import shutil
import subprocess
from pathlib import Path

import pytest

from backend.app.git_intelligence.service import GitIntelligenceService


def test_non_git_directory_returns_empty_result(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")

    result = GitIntelligenceService().analyze_repository(tmp_path)

    assert result.recent_commits == []
    assert result.change_frequency == []
    assert result.blame == []


def test_recent_commits_are_extracted_from_temp_git_repo(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path)

    result = GitIntelligenceService().analyze_repository(repo, limit=2)

    assert len(result.recent_commits) == 2
    assert result.recent_commits[0].message == "Update app"
    assert result.recent_commits[0].commit_hash
    assert result.recent_commits[0].short_hash
    assert result.recent_commits[0].author_name == "Repo Pilot"
    assert result.recent_commits[0].author_email == "repo@example.com"


def test_changed_files_are_captured(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path)

    result = GitIntelligenceService().analyze_repository(repo, limit=2)

    changed_files = {
        file_path
        for commit in result.recent_commits
        for file_path in commit.changed_files
    }
    assert "app/main.py" in changed_files
    assert all(not Path(file_path).is_absolute() for file_path in changed_files)


def test_file_change_frequency_is_calculated(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path)

    result = GitIntelligenceService().analyze_repository(repo)

    frequency = {item.file_path: item for item in result.change_frequency}
    assert frequency["app/main.py"].commit_count == 2
    assert frequency["app/main.py"].last_modified_commit
    assert frequency["app/main.py"].last_modified_at is not None
    assert frequency["README.md"].commit_count == 1


def test_blame_returns_line_level_metadata_for_file(tmp_path: Path) -> None:
    repo = _create_git_repo(tmp_path)

    result = GitIntelligenceService().analyze_repository(
        repo,
        blame_file_path="app/main.py",
    )

    assert result.blame
    first_line = result.blame[0]
    assert first_line.file_path == "app/main.py"
    assert first_line.line_number == 1
    assert first_line.commit_hash
    assert first_line.author_name == "Repo Pilot"
    assert first_line.committed_at is not None
    assert "print" in first_line.line_content


def _create_git_repo(tmp_path: Path) -> Path:
    if shutil.which("git") is None:
        pytest.skip("git executable is not available")

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Repo Pilot")
    _git(repo, "config", "user.email", "repo@example.com")

    app = repo / "app"
    app.mkdir()
    (app / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Initial commit")

    (app / "main.py").write_text(
        "print('hello')\nprint('updated')\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Update app")
    return repo


def _git(repo: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
