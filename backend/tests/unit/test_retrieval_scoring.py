from backend.app.retrieval.service import RetrievalService
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.intelligence import (
    ImportInfo,
    PythonFileSymbols,
    RouteIndex,
    RouteInfo,
    SymbolIndex,
)
from backend.app.schemas.retrieval import RetrievalInput
from backend.app.schemas.scan import FileType, ScannedFile


def _file(path: str, file_type: FileType = FileType.python) -> ScannedFile:
    return ScannedFile(path=path, file_type=file_type, size_bytes=100)


def test_cors_issue_prioritizes_setup_and_configuration_files() -> None:
    request = RetrievalInput(
        issue_text="FastAPI CORS middleware configuration is broken",
        scanned_files=[
            _file("main.py"),
            _file("app.py"),
            _file("config.py"),
            _file("routes/users.py"),
        ],
        framework=SupportedFramework.fastapi,
    )

    result = RetrievalService().retrieve(request)

    assert [item.file_path for item in result.files[:3]] == [
        "main.py",
        "app.py",
        "config.py",
    ]
    assert "keyword:cors" in result.files[0].matched_signals


def test_login_issue_prioritizes_matching_route() -> None:
    request = RetrievalInput(
        issue_text="POST /api/login returns 500",
        scanned_files=[
            _file("main.py"),
            _file("routes/auth.py"),
            _file("models/user.py"),
        ],
        framework=SupportedFramework.fastapi,
        route_index=RouteIndex(
            routes=[
                RouteInfo(
                    framework=SupportedFramework.fastapi,
                    path="/api/login",
                    method="POST",
                    handler_name="login",
                    file_path="routes/auth.py",
                    line_number=10,
                    router_name="router",
                )
            ]
        ),
    )

    result = RetrievalService().retrieve(request)

    assert result.files[0].file_path == "routes/auth.py"
    assert "route:/api/login" in result.files[0].matched_signals


def test_import_error_prioritizes_mentioned_file_and_matching_import() -> None:
    request = RetrievalInput(
        issue_text="ImportError in services/user_service.py: No module named 'sqlalchemy'",
        scanned_files=[
            _file("main.py"),
            _file("services/user_service.py"),
            _file("database/models.py"),
        ],
        framework=SupportedFramework.flask,
        symbol_index=SymbolIndex(
            files=[
                PythonFileSymbols(
                    path="database/models.py",
                    imports=[ImportInfo(module="sqlalchemy")],
                )
            ]
        ),
    )

    result = RetrievalService().retrieve(request)

    assert result.files[0].file_path == "services/user_service.py"
    assert "file:user_service.py" in result.files[0].matched_signals
    matching_import = next(
        item for item in result.files if item.file_path == "database/models.py"
    )
    assert "import:sqlalchemy" in matching_import.matched_signals


def test_unknown_issue_returns_stable_reasonable_top_n() -> None:
    request = RetrievalInput(
        issue_text="Something unexpected happens",
        scanned_files=[
            _file("z.py"),
            _file("main.py"),
            _file("README.md", FileType.markdown),
            _file("a.py"),
        ],
        framework=SupportedFramework.fastapi,
        top_n=2,
    )

    result = RetrievalService().retrieve(request)

    assert [item.file_path for item in result.files] == ["main.py", "a.py"]
    assert all(0.0 <= item.score <= 1.0 for item in result.files)
