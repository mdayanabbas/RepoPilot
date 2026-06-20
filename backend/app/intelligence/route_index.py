from pathlib import Path

from backend.app.intelligence.fastapi_extractor import extract_fastapi_routes
from backend.app.intelligence.flask_extractor import extract_flask_routes
from backend.app.intelligence.python_ast_parser import parse_python_file
from backend.app.scanner.file_tree import scan_file_tree
from backend.app.scanner.ignore_rules import is_ignored_directory, is_ignored_file
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.intelligence import RouteIndex
from backend.app.schemas.scan import FileType, ScanResult


def build_route_index(
    repo_path: str | Path,
    framework: SupportedFramework | None = None,
    scan_result: ScanResult | None = None,
) -> RouteIndex:
    root = Path(repo_path).resolve()
    scan = scan_result or scan_file_tree(root)
    index = RouteIndex()

    for scanned_file in scan.files:
        if scanned_file.file_type not in {FileType.python, FileType.test}:
            continue
        relative_path = Path(scanned_file.path)
        if is_ignored_file(relative_path) or any(
            is_ignored_directory(part) for part in relative_path.parts[:-1]
        ):
            continue
        parsed_file = parse_python_file(root / relative_path, root)
        if parsed_file.error:
            index.errors.append(parsed_file.error)
            continue
        if parsed_file.tree is None:
            continue
        if framework in {None, SupportedFramework.fastapi}:
            index.routes.extend(extract_fastapi_routes(parsed_file.tree, parsed_file.path))
        if framework in {None, SupportedFramework.flask}:
            index.routes.extend(extract_flask_routes(parsed_file.tree, parsed_file.path))
    return index


class RouteIndexer:
    def build(
        self,
        repo_path: str | Path,
        framework: SupportedFramework | None = None,
        scan_result: ScanResult | None = None,
    ) -> RouteIndex:
        return build_route_index(repo_path, framework, scan_result)
