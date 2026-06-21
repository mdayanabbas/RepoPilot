import ast
from pathlib import Path


def extract_imports(file_path: str | Path) -> set[str]:
    source_code = Path(file_path).read_text(encoding="utf-8")

    tree = ast.parse(source_code)

    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports