from flask import Blueprint, jsonify, request

from services.auth_service import authenticate_user

auth_blueprint = Blueprint("auth", __name__, url_prefix="/api")


@auth_blueprint.route("/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")

    token = authenticate_user(username, password)
    if token is None:
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"access_token": token, "token_type": "bearer"})
