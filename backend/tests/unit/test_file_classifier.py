import pytest

from backend.app.scanner.file_classifier import classify_file
from backend.app.schemas.scan import FileType


@pytest.mark.parametrize(
    ("file_name", "expected_type"),
    [
        ("main.py", FileType.python),
        ("test_main.py", FileType.test),
        ("service_test.py", FileType.test),
        ("pyproject.toml", FileType.config),
        ("setup.cfg", FileType.config),
        ("README.md", FileType.markdown),
        ("package.json", FileType.json),
        ("config.yaml", FileType.yaml),
        ("config.yml", FileType.yaml),
        (".env", FileType.env),
        (".env.local", FileType.env),
        ("notes.txt", FileType.text),
        ("archive.zip", FileType.unknown),
    ],
)
def test_classify_file_returns_expected_type(file_name: str, expected_type: FileType) -> None:
    assert classify_file(file_name) == expected_type


def test_python_test_files_are_classified_as_test_not_python() -> None:
    assert classify_file("test_routes.py") == FileType.test
    assert classify_file("routes_test.py") == FileType.test
