from collections import Counter
import os
from pathlib import Path

from backend.app.core.errors import ScanError
from backend.app.scanner.file_classifier import classify_file
from backend.app.scanner.ignore_rules import is_ignored_directory, is_ignored_file
from backend.app.schemas.scan import FileType, ScanResult, ScannedFile


def scan_file_tree(repo_path: str | Path) -> ScanResult:
    root = Path(repo_path)
    if not root.exists():
        raise ScanError("Scan path does not exist", details={"path": str(repo_path)})
    if not root.is_dir():
        raise ScanError("Scan path must be a directory", details={"path": str(repo_path)})

    scanned_files: list[ScannedFile] = []

    for current_root_string, dir_names, file_names in os.walk(root):
        current_root = Path(current_root_string)
        dir_names[:] = sorted(
            directory for directory in dir_names if not is_ignored_directory(directory)
        )

        for file_name in sorted(file_names):
            file_path = current_root / file_name
            if is_ignored_file(file_path):
                continue

            relative_path = file_path.relative_to(root).as_posix()
            scanned_files.append(
                ScannedFile(
                    path=relative_path,
                    file_type=classify_file(file_path),
                    size_bytes=file_path.stat().st_size,
                )
            )

    counts = Counter(scanned_file.file_type for scanned_file in scanned_files)
    return ScanResult(
        total_files=len(scanned_files),
        python_files=counts[FileType.python],
        test_files=counts[FileType.test],
        config_files=counts[FileType.config],
        markdown_files=counts[FileType.markdown],
        json_files=counts[FileType.json],
        yaml_files=counts[FileType.yaml],
        env_files=counts[FileType.env],
        text_files=counts[FileType.text],
        unknown_files=counts[FileType.unknown],
        files=scanned_files,
    )
