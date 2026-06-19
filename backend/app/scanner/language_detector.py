from pathlib import Path

from backend.app.scanner.file_classifier import classify_file
from backend.app.schemas.scan import FileType


def detect_language(path: str | Path) -> str:
    file_type = classify_file(path)
    if file_type in {FileType.python, FileType.test}:
        return "python"
    if file_type == FileType.markdown:
        return "markdown"
    if file_type == FileType.json:
        return "json"
    if file_type == FileType.yaml:
        return "yaml"
    if file_type == FileType.text:
        return "text"
    return "unknown"
