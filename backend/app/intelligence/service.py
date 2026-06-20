from pathlib import Path

from backend.app.intelligence.python_ast_parser import parse_python_file
from backend.app.intelligence.symbol_index import index_parsed_file
from backend.app.scanner.file_tree import scan_file_tree
from backend.app.scanner.ignore_rules import is_ignored_directory, is_ignored_file
from backend.app.schemas.intelligence import SymbolIndex
from backend.app.schemas.scan import FileType, ScanResult


class IntelligenceService:
    def analyze_repository(
        self,
        repo_path: str | Path,
        scan_result: ScanResult | None = None,
    ) -> SymbolIndex:
        root = Path(repo_path).resolve()
        scan = scan_result or scan_file_tree(root)
        index = SymbolIndex()

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
            else:
                index.files.append(index_parsed_file(parsed_file))

        return index


def analyze_repository(
    repo_path: str | Path,
    scan_result: ScanResult | None = None,
) -> SymbolIndex:
    return IntelligenceService().analyze_repository(repo_path, scan_result)
