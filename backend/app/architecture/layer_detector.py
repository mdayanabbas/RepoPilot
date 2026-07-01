from pathlib import PurePosixPath

from backend.app.schemas.architecture import ArchitectureNodeType
from backend.app.schemas.scan import FileType, ScannedFile


def detect_file_layer(scanned_file: ScannedFile) -> ArchitectureNodeType:
    path = PurePosixPath(scanned_file.path)
    lowered_parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    stem = path.stem.lower()

    if scanned_file.file_type == FileType.config or stem in {"config", "settings"}:
        return ArchitectureNodeType.config
    if name in {"main.py", "app.py"}:
        return ArchitectureNodeType.file
    if _contains(
        lowered_parts,
        {"route", "routes", "router", "routers", "controller", "controllers"},
    ):
        return ArchitectureNodeType.route
    if _contains(lowered_parts, {"service", "services"}):
        return ArchitectureNodeType.service
    if _contains(lowered_parts, {"repository", "repositories", "repo", "repos"}):
        return ArchitectureNodeType.repository
    if _contains(lowered_parts, {"model", "models", "schema", "schemas"}):
        return ArchitectureNodeType.model
    if _contains(lowered_parts, {"database", "databases", "db", "session", "sessions"}):
        return ArchitectureNodeType.database
    if scanned_file.file_type == FileType.python:
        return ArchitectureNodeType.file
    return ArchitectureNodeType.unknown


def is_entrypoint(scanned_file: ScannedFile) -> bool:
    name = PurePosixPath(scanned_file.path).name.lower()
    return name in {"main.py", "app.py"}


def _contains(values: list[str], options: set[str]) -> bool:
    return any(value in options for value in values)
