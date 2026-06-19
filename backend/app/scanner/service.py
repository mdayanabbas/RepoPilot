from pathlib import Path

from backend.app.scanner.file_tree import scan_file_tree
from backend.app.schemas.scan import ScanResult


class ScannerService:
    def scan_repository(self, repo_path: str | Path) -> ScanResult:
        return scan_file_tree(repo_path)
