import ast

from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.intelligence import RouteInfo

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}


def extract_fastapi_routes(tree: ast.Module, file_path: str) -> list[RouteInfo]:
    prefixes = _router_prefixes(tree)
    routes: list[RouteInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            route = _extract_route(decorator, node, file_path, prefixes)
            if route:
                routes.append(route)
    return routes


def _extract_route(
    decorator: ast.expr,
    handler: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
    prefixes: dict[str, str],
) -> RouteInfo | None:
    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
        return None
    if decorator.func.attr.lower() not in HTTP_METHODS:
        return None
    router_name = _name(decorator.func.value)
    path = _string_argument(decorator, "path")
    if router_name is None or path is None:
        return None
    return RouteInfo(
        framework=SupportedFramework.fastapi,
        path=_join_paths(prefixes.get(router_name, ""), path),
        method=decorator.func.attr.upper(),
        handler_name=handler.name,
        file_path=file_path,
        line_number=handler.lineno,
        router_name=router_name,
    )


def _router_prefixes(tree: ast.Module) -> dict[str, str]:
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
        if _name(value.func) not in {"APIRouter", "fastapi.APIRouter"}:
            continue
        prefix = _keyword_string(value, "prefix")
        if prefix is not None:
            prefixes[target.id] = prefix
    return prefixes


def _name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _name(node.value)
        return f"{owner}.{node.attr}" if owner else node.attr
    return None


def _string_argument(call: ast.Call, keyword: str) -> str | None:
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return _keyword_string(call, keyword)


def _keyword_string(call: ast.Call, keyword: str) -> str | None:
    for item in call.keywords:
        if item.arg == keyword and isinstance(item.value, ast.Constant):
            return item.value.value if isinstance(item.value.value, str) else None
    return None


def _join_paths(prefix: str, path: str) -> str:
    if not prefix:
        return path
    if path == "/":
        return f"{prefix.rstrip('/')}/"
    return f"{prefix.rstrip('/')}/{path.lstrip('/')}"
