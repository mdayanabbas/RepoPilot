from flask import Flask

from routes.auth import auth_blueprint

app = Flask(__name__)
app.register_blueprint(auth_blueprint)


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200
