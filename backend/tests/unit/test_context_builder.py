from pathlib import Path

import pytest

from backend.app.core.errors import RetrievalError
from backend.app.retrieval.context_builder import ContextBuilder
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.retrieval import ContextBuildInput, RelevantFile


def _selected(path: str) -> RelevantFile:
    return RelevantFile(
        file_path=path,
        score=0.8,
        reason="Selected for test",
        matched_signals=["test"],
    )


def _input(workspace: Path, paths: list[str], **limits: int) -> ContextBuildInput:
    return ContextBuildInput(
        issue_text="The application fails",
        workspace_path=str(workspace),
        framework=SupportedFramework.fastapi,
        selected_files=[_selected(path) for path in paths],
        **limits,
    )


def test_context_reads_only_selected_files(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("selected = True\n", encoding="utf-8")
    (tmp_path / "secret.py").write_text("not_selected = True\n", encoding="utf-8")

    result = ContextBuilder().build(_input(tmp_path, ["main.py"]))

    assert [file.file_path for file in result.file_contexts] == ["main.py"]
    assert result.file_contexts[0].content == "selected = True\n"
    assert "not_selected" not in result.file_contexts[0].content


def test_per_file_truncation(tmp_path: Path) -> None:
    (tmp_path / "large.py").write_text("abcdefghij", encoding="utf-8")

    result = ContextBuilder().build(
        _input(tmp_path, ["large.py"], max_file_chars=5, max_context_chars=100)
    )

    assert result.file_contexts[0].content == "abcde"
    assert result.file_contexts[0].truncated is True
    assert result.total_context_chars == 5


def test_total_context_limit_is_shared_between_files(tmp_path: Path) -> None:
    (tmp_path / "first.py").write_text("abcdef", encoding="utf-8")
    (tmp_path / "second.py").write_text("ghijkl", encoding="utf-8")

    result = ContextBuilder().build(
        _input(
            tmp_path,
            ["first.py", "second.py"],
            max_file_chars=10,
            max_context_chars=8,
        )
    )

    assert [file.content for file in result.file_contexts] == ["abcdef", "gh"]
    assert result.file_contexts[1].truncated is True
    assert result.total_context_chars == 8


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.py"
    outside.write_text("secret = True", encoding="utf-8")

    with pytest.raises(RetrievalError):
        ContextBuilder().build(_input(tmp_path, ["../outside.py"]))


def test_missing_file_is_handled_safely(tmp_path: Path) -> None:
    result = ContextBuilder().build(_input(tmp_path, ["missing.py"]))

    assert result.file_contexts[0].content == ""
    assert result.file_contexts[0].error == "File does not exist"
    assert result.total_context_chars == 0


def test_binary_and_ignored_files_are_not_included(tmp_path: Path) -> None:
    (tmp_path / "binary.py").write_bytes(b"\x00\x01\x02")
    ignored = tmp_path / ".venv"
    ignored.mkdir()
    (ignored / "hidden.py").write_text("secret = True", encoding="utf-8")

    result = ContextBuilder().build(_input(tmp_path, ["binary.py", ".venv/hidden.py"]))

    assert [file.content for file in result.file_contexts] == ["", ""]
    assert result.file_contexts[0].error == "Binary or unreadable file"
    assert result.file_contexts[1].error == "Ignored file"
