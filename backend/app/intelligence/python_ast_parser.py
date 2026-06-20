import ast
import tokenize
from dataclasses import dataclass
from pathlib import Path

from backend.app.schemas.intelligence import IntelligenceErrorEntry


@dataclass(frozen=True, slots=True)
class ParsedPythonFile:
    path: str
    tree: ast.Module | None
    error: IntelligenceErrorEntry | None = None


def parse_python_source(source: str, filename: str = "<unknown>") -> ast.Module:
    return ast.parse(source, filename=filename)


def parse_python_file(path: str | Path, root: str | Path) -> ParsedPythonFile:
    file_path = Path(path).resolve()
    root_path = Path(root).resolve()
    relative_path = file_path.relative_to(root_path).as_posix()

    try:
        with tokenize.open(file_path) as source_file:
            tree = parse_python_source(source_file.read(), filename=relative_path)
    except SyntaxError as exc:
        return ParsedPythonFile(
            path=relative_path,
            tree=None,
            error=IntelligenceErrorEntry(
                path=relative_path,
                message=exc.msg,
                line_number=exc.lineno,
            ),
        )
    except (OSError, UnicodeError) as exc:
        return ParsedPythonFile(
            path=relative_path,
            tree=None,
            error=IntelligenceErrorEntry(path=relative_path, message=str(exc)),
        )

    return ParsedPythonFile(path=relative_path, tree=tree)


class PythonAstParser:
    def parse_source(self, source: str, filename: str = "<unknown>") -> ast.Module:
        return parse_python_source(source, filename)

    def parse_file(self, path: str | Path, root: str | Path) -> ParsedPythonFile:
        return parse_python_file(path, root)
