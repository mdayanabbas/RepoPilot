import ast

from backend.app.intelligence.function_extractor import extract_function
from backend.app.schemas.intelligence import ClassInfo


def extract_class(node: ast.ClassDef) -> ClassInfo:
    methods = [
        extract_function(child)
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    return ClassInfo(
        name=node.name,
        line_number=node.lineno,
        base_classes=[ast.unparse(base) for base in node.bases],
        methods=methods,
    )


def extract_classes(tree: ast.Module) -> list[ClassInfo]:
    return [extract_class(node) for node in tree.body if isinstance(node, ast.ClassDef)]
