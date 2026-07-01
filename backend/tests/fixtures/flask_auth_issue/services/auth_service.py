USERS = {
    "demo@example.com": {
        "password": "secret",
        "token": "demo-token",
        "active": True,
    }
}


def authenticate_user(username: str, password: str) -> str | None:
    user = USERS.get(username)
    if user is None or not user["active"]:
        return None
    if password != user["password"]:
        return None
    return user["token"]
