from pathlib import Path

from backend.app.intelligence.route_index import build_route_index
from backend.app.schemas.framework import SupportedFramework


def test_extracts_flask_routes_methods_defaults_and_blueprint_prefix(tmp_path: Path) -> None:
    source = '''from flask import Blueprint, Flask

app = Flask(__name__)
blueprint = Blueprint("api", __name__, url_prefix="/api")

@app.route("/health")
def health():
    return "ok"

@app.route("/users", methods=["POST"])
def create_user():
    return "created"

@blueprint.route("/items", methods=["GET", "POST"])
def items():
    return "items"
'''
    (tmp_path / "app.py").write_text(source, encoding="utf-8")

    result = build_route_index(tmp_path, SupportedFramework.flask)

    assert result.errors == []
    assert [(route.method, route.path) for route in result.routes] == [
        ("GET", "/health"),
        ("POST", "/users"),
        ("GET", "/api/items"),
        ("POST", "/api/items"),
    ]
    assert result.routes[0].framework == SupportedFramework.flask
    assert result.routes[0].handler_name == "health"
    assert result.routes[0].file_path == "app.py"
    assert result.routes[0].line_number == 7
    assert result.routes[2].router_name == "blueprint"


def test_flask_syntax_error_is_safe(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("@app.route('/bad')\ndef broken(:", encoding="utf-8")

    result = build_route_index(tmp_path, SupportedFramework.flask)

    assert result.routes == []
    assert result.errors[0].path == "broken.py"
