from pathlib import Path

from backend.app.intelligence.route_index import build_route_index
from backend.app.schemas.framework import SupportedFramework


def test_extracts_fastapi_routes_and_router_prefix(tmp_path: Path) -> None:
    source = '''from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix="/api")

@app.get("/health")
def health():
    return {}

@app.post("/users")
async def create_user():
    return {}

@router.put("/users/{user_id}")
def update_user(user_id: int):
    return {}

@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    return {}

@router.patch("/users/{user_id}")
def patch_user(user_id: int):
    return {}
'''
    nested = tmp_path / "routes"
    nested.mkdir()
    (nested / "users.py").write_text(source, encoding="utf-8")

    result = build_route_index(tmp_path, SupportedFramework.fastapi)

    assert result.errors == []
    assert [(route.method, route.path) for route in result.routes] == [
        ("GET", "/health"),
        ("POST", "/users"),
        ("PUT", "/api/users/{user_id}"),
        ("DELETE", "/api/users/{user_id}"),
        ("PATCH", "/api/users/{user_id}"),
    ]
    assert result.routes[0].framework == SupportedFramework.fastapi
    assert result.routes[0].handler_name == "health"
    assert result.routes[0].file_path == "routes/users.py"
    assert result.routes[0].line_number == 7
    assert result.routes[2].router_name == "router"


def test_fastapi_syntax_error_is_safe(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("@app.get('/bad')\ndef broken(:", encoding="utf-8")

    result = build_route_index(tmp_path, SupportedFramework.fastapi)

    assert result.routes == []
    assert result.errors[0].path == "broken.py"
