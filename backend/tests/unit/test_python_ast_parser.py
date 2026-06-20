from pathlib import Path

from backend.app.intelligence.service import IntelligenceService


def test_extracts_imports_functions_classes_and_decorators(tmp_path: Path) -> None:
    source = '''import os
import json as json_lib
from pathlib import Path

def traced(function):
    return function

@traced
def greet(name: str, greeting="hello", *, excited=False):
    return greeting

@classmethod
async def fetch(cls, item_id, *values, **options):
    return item_id

class Handler(object):
    def handle(self, request):
        return request

    @staticmethod
    async def close(code=0):
        return code
'''
    (tmp_path / "app.py").write_text(source, encoding="utf-8")

    result = IntelligenceService().analyze_repository(tmp_path)

    assert result.errors == []
    assert len(result.files) == 1
    symbols = result.files[0]
    assert symbols.path == "app.py"
    assert [(item.module, item.name) for item in symbols.imports] == [
        ("os", None),
        ("json", None),
        ("pathlib", "Path"),
    ]
    assert [function.name for function in symbols.functions] == ["traced", "greet", "fetch"]
    assert symbols.functions[1].args == ["name", "greeting", "excited"]
    assert symbols.functions[1].decorators == ["traced"]
    assert symbols.functions[1].is_async is False
    assert symbols.functions[2].args == ["cls", "item_id", "*values", "**options"]
    assert symbols.functions[2].decorators == ["classmethod"]
    assert symbols.functions[2].is_async is True
    assert symbols.functions[1].line_number == 9

    extracted_class = symbols.classes[0]
    assert extracted_class.name == "Handler"
    assert extracted_class.base_classes == ["object"]
    assert [method.name for method in extracted_class.methods] == ["handle", "close"]
    assert extracted_class.methods[1].decorators == ["staticmethod"]
    assert extracted_class.methods[1].is_async is True


def test_syntax_error_is_reported_and_file_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "valid.py").write_text("def valid():\n    pass\n", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def broken(:\n    pass\n", encoding="utf-8")

    result = IntelligenceService().analyze_repository(tmp_path)

    assert [file.path for file in result.files] == ["valid.py"]
    assert len(result.errors) == 1
    assert result.errors[0].path == "broken.py"
    assert result.errors[0].line_number == 1


def test_ignored_python_files_are_not_read(tmp_path: Path) -> None:
    ignored = tmp_path / ".venv"
    ignored.mkdir()
    (ignored / "broken.py").write_text("def broken(:", encoding="utf-8")
    (tmp_path / "main.py").write_text("import sys\n", encoding="utf-8")

    result = IntelligenceService().analyze_repository(tmp_path)

    assert [file.path for file in result.files] == ["main.py"]
    assert result.errors == []
