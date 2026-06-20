import ast

from backend.app.schemas.intelligence import ImportInfo


def extract_imports(tree: ast.AST) -> list[ImportInfo]:
    imports: list[ImportInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(ImportInfo(module=alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = f"{'.' * node.level}{node.module or ''}"
            imports.extend(ImportInfo(module=module, name=alias.name) for alias in node.names)
    return imports
