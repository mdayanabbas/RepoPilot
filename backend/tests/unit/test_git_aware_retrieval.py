from datetime import datetime, timezone

from backend.app.retrieval.service import RetrievalService
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.git_intelligence import (
    FileChangeFrequency,
    GitCommitInfo,
    GitHistoryResult,
)
from backend.app.schemas.intelligence import RouteIndex, RouteInfo
from backend.app.schemas.retrieval import RelevantFile, RetrievalInput
from backend.app.schemas.scan import FileType, ScannedFile


def test_recent_file_gets_boosted() -> None:
    result = RetrievalService().retrieve(
        RetrievalInput(
            issue_text="Something unexpected happens",
            scanned_files=[_file("a.py"), _file("b.py")],
            framework=SupportedFramework.unknown,
            git_history=GitHistoryResult(
                recent_commits=[_commit("Recent change", ["b.py"])]
            ),
        )
    )

    boosted = _find(result.files, "b.py")
    assert "recently_changed" in boosted.matched_signals
    assert boosted.score > _find(result.files, "a.py").score


def test_high_churn_file_gets_boosted() -> None:
    result = RetrievalService().retrieve(
        RetrievalInput(
            issue_text="Something unexpected happens",
            scanned_files=[_file("stable.py"), _file("churn.py")],
            framework=SupportedFramework.unknown,
            git_history=GitHistoryResult(
                change_frequency=[
                    _frequency("churn.py", 4),
                    _frequency("stable.py", 1),
                ]
            ),
        )
    )

    boosted = _find(result.files, "churn.py")
    assert "high_change_frequency" in boosted.matched_signals
    assert boosted.score > _find(result.files, "stable.py").score


def test_commit_message_matching_issue_boosts_file() -> None:
    result = RetrievalService().retrieve(
        RetrievalInput(
            issue_text="Login returns 500",
            scanned_files=[_file("main.py"), _file("routes/auth.py")],
            framework=SupportedFramework.unknown,
            git_history=GitHistoryResult(
                recent_commits=[_commit("Fix login bug", ["routes/auth.py"])]
            ),
        )
    )

    boosted = _find(result.files, "routes/auth.py")
    assert "commit_message_match" in boosted.matched_signals
    assert boosted.score > _find(result.files, "main.py").score


def test_no_git_history_does_not_break_retrieval() -> None:
    result = RetrievalService().retrieve(
        RetrievalInput(
            issue_text="Something unexpected happens",
            scanned_files=[_file("a.py"), _file("b.py")],
            framework=SupportedFramework.unknown,
        )
    )

    assert [item.file_path for item in result.files] == ["a.py", "b.py"]
    assert all("recently_changed" not in item.matched_signals for item in result.files)


def test_route_match_still_outranks_unrelated_high_churn_file() -> None:
    result = RetrievalService().retrieve(
        RetrievalInput(
            issue_text="POST /api/login returns 500",
            scanned_files=[
                _file("routes/auth.py"),
                _file("unrelated/churn.py"),
            ],
            framework=SupportedFramework.fastapi,
            route_index=RouteIndex(
                routes=[
                    RouteInfo(
                        framework=SupportedFramework.fastapi,
                        path="/api/login",
                        method="POST",
                        handler_name="login",
                        file_path="routes/auth.py",
                        line_number=10,
                    )
                ]
            ),
            git_history=GitHistoryResult(
                change_frequency=[_frequency("unrelated/churn.py", 10)]
            ),
        )
    )

    assert result.files[0].file_path == "routes/auth.py"
    churn = _find(result.files, "unrelated/churn.py")
    assert "high_change_frequency" in churn.matched_signals


def _file(path: str) -> ScannedFile:
    return ScannedFile(path=path, file_type=FileType.python, size_bytes=100)


def _commit(message: str, changed_files: list[str]) -> GitCommitInfo:
    return GitCommitInfo(
        commit_hash="a" * 40,
        short_hash="a" * 7,
        author_name="Repo Pilot",
        author_email="repo@example.com",
        committed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        message=message,
        changed_files=changed_files,
    )


def _frequency(file_path: str, commit_count: int) -> FileChangeFrequency:
    return FileChangeFrequency(
        file_path=file_path,
        commit_count=commit_count,
        last_modified_commit="a" * 40,
        last_modified_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _find(files: list[RelevantFile], file_path: str) -> RelevantFile:
    return next(item for item in files if item.file_path == file_path)
