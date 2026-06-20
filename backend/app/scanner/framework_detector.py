import re
from pathlib import Path

from backend.app.schemas.framework import (
    FrameworkDetectionResult,
    FrameworkSignal,
    SupportedFramework,
)
from backend.app.schemas.scan import FileType, ScanResult, ScannedFile

MAX_FILE_READ_BYTES = 64_000

FASTAPI_DEPENDENCY_PATTERN = re.compile(r"(^|[^a-z0-9_-])fastapi([^a-z0-9_-]|$)", re.I)
FLASK_DEPENDENCY_PATTERN = re.compile(r"(^|[^a-z0-9_-])flask([^a-z0-9_-]|$)", re.I)

FASTAPI_IMPORT_PATTERNS = (
    re.compile(r"^\s*from\s+fastapi\s+import\s+.*\bFastAPI\b", re.M),
    re.compile(r"^\s*import\s+fastapi\b", re.M),
)
FLASK_IMPORT_PATTERNS = (
    re.compile(r"^\s*from\s+flask\s+import\s+.*\bFlask\b", re.M),
    re.compile(r"^\s*import\s+flask\b", re.M),
)

FASTAPI_APP_PATTERN = re.compile(r"\bFastAPI\s*\(")
FLASK_APP_PATTERN = re.compile(r"\bFlask\s*\(\s*__name__\s*\)")

DEPENDENCY_FILES = {"requirements.txt", "pyproject.toml"}


def detect_framework(repo_path: str | Path, scan_result: ScanResult) -> FrameworkDetectionResult:
    root = Path(repo_path)
    signals: list[FrameworkSignal] = []

    for scanned_file in scan_result.files:
        if scanned_file.size_bytes > MAX_FILE_READ_BYTES:
            continue

        if _is_dependency_file(scanned_file):
            contents = _read_limited_text(root / scanned_file.path)
            signals.extend(_detect_dependency_signals(scanned_file.path, contents))
            continue

        if scanned_file.file_type in {FileType.python, FileType.test}:
            contents = _read_limited_text(root / scanned_file.path)
            signals.extend(_detect_python_signals(scanned_file.path, contents))

    return _build_result(signals)


def _is_dependency_file(scanned_file: ScannedFile) -> bool:
    return Path(scanned_file.path).name.lower() in DEPENDENCY_FILES


def _read_limited_text(path: Path) -> str:
    data = path.read_bytes()[:MAX_FILE_READ_BYTES]
    return data.decode("utf-8", errors="ignore")


def _detect_dependency_signals(path: str, contents: str) -> list[FrameworkSignal]:
    signals: list[FrameworkSignal] = []
    if FASTAPI_DEPENDENCY_PATTERN.search(contents):
        signals.append(
            FrameworkSignal(
                framework=SupportedFramework.fastapi,
                source=path,
                message="Dependency file references fastapi",
                weight=0.45,
            )
        )
    if FLASK_DEPENDENCY_PATTERN.search(contents):
        signals.append(
            FrameworkSignal(
                framework=SupportedFramework.flask,
                source=path,
                message="Dependency file references flask",
                weight=0.45,
            )
        )
    return signals


def _detect_python_signals(path: str, contents: str) -> list[FrameworkSignal]:
    signals: list[FrameworkSignal] = []
    if any(pattern.search(contents) for pattern in FASTAPI_IMPORT_PATTERNS):
        signals.append(
            FrameworkSignal(
                framework=SupportedFramework.fastapi,
                source=path,
                message="Python file imports FastAPI",
                weight=0.35,
            )
        )
    if FASTAPI_APP_PATTERN.search(contents):
        signals.append(
            FrameworkSignal(
                framework=SupportedFramework.fastapi,
                source=path,
                message="Python file creates FastAPI application",
                weight=0.30,
            )
        )
    if any(pattern.search(contents) for pattern in FLASK_IMPORT_PATTERNS):
        signals.append(
            FrameworkSignal(
                framework=SupportedFramework.flask,
                source=path,
                message="Python file imports Flask",
                weight=0.35,
            )
        )
    if FLASK_APP_PATTERN.search(contents):
        signals.append(
            FrameworkSignal(
                framework=SupportedFramework.flask,
                source=path,
                message="Python file creates Flask application",
                weight=0.30,
            )
        )
    return signals


def _build_result(signals: list[FrameworkSignal]) -> FrameworkDetectionResult:
    if not signals:
        return FrameworkDetectionResult(
            framework=SupportedFramework.unknown,
            confidence=0.05,
            signals=[],
        )

    scores = {
        SupportedFramework.fastapi: 0.0,
        SupportedFramework.flask: 0.0,
    }
    for signal in signals:
        if signal.framework in scores:
            scores[signal.framework] += signal.weight

    framework = max(scores, key=scores.get)
    confidence = min(scores[framework], 1.0)

    if confidence == 0:
        framework = SupportedFramework.unknown
        confidence = 0.05

    return FrameworkDetectionResult(
        framework=framework,
        confidence=confidence,
        signals=[signal for signal in signals if signal.framework == framework],
    )
