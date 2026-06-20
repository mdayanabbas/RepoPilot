import ast

from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.intelligence import RouteInfo


def extract_flask_routes(tree: ast.Module, file_path: str) -> list[RouteInfo]:
    prefixes = _blueprint_prefixes(tree)
    routes: list[RouteInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            routes.extend(_extract_routes(decorator, node, file_path, prefixes))
    return routes


def _extract_routes(
    decorator: ast.expr,
    handler: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
    prefixes: dict[str, str],
) -> list[RouteInfo]:
    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
        return []
    if decorator.func.attr != "route" or not isinstance(decorator.func.value, ast.Name):
        return []
    router_name = decorator.func.value.id
    path = _string_argument(decorator)
    if path is None:
        return []
    methods = _methods(decorator)
    return [
        RouteInfo(
            framework=SupportedFramework.flask,
            path=_join_paths(prefixes.get(router_name, ""), path),
            method=method,
            handler_name=handler.name,
            file_path=file_path,
            line_number=handler.lineno,
            router_name=router_name,
        )
        for method in methods
    ]


def _blueprint_prefixes(tree: ast.Module) -> dict[str, str]:
    prefixes: dict[str, str] = {}
    for node in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Call):
            continue
        if not isinstance(value.func, ast.Name) or value.func.id != "Blueprint":
            continue
        prefix = _keyword_string(value, "url_prefix")
        if prefix is not None:
            prefixes[target.id] = prefix
    return prefixes


def _string_argument(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return _keyword_string(call, "rule")


def _methods(call: ast.Call) -> list[str]:
    for keyword in call.keywords:
        if keyword.arg != "methods":
            continue
        if not isinstance(keyword.value, (ast.List, ast.Tuple, ast.Set)):
            return []
        return [
            item.value.upper()
            for item in keyword.value.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ]
    return ["GET"]


def _keyword_string(call: ast.Call, name: str) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value if isinstance(keyword.value.value, str) else None
    return None


def _join_paths(prefix: str, path: str) -> str:
    if not prefix:
        return path
    if path == "/":
        return f"{prefix.rstrip('/')}/"
    return f"{prefix.rstrip('/')}/{path.lstrip('/')}"
