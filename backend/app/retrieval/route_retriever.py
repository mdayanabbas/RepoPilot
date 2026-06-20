import re

from backend.app.retrieval.scoring import SignalMap, add_signal
from backend.app.schemas.intelligence import RouteIndex

PATH_PATTERN = re.compile(r"/[a-zA-Z0-9_{}./-]+")


def add_route_signals(
    issue_text: str, route_index: RouteIndex, signals: SignalMap
) -> None:
    issue = issue_text.lower()
    mentioned_paths = {path.rstrip(".,;:)") for path in PATH_PATTERN.findall(issue)}
    auth_issue = any(word in issue for word in ("login", "auth", "sign in", "signin"))

    for route in route_index.routes:
        route_path = route.path.lower()
        if route_path in mentioned_paths:
            add_signal(
                signals,
                route.file_path,
                f"route:{route.path}",
                0.65,
                f"Defines the mentioned route {route.path}",
            )
        elif auth_issue and any(
            segment in route_path for segment in ("login", "auth", "signin")
        ):
            add_signal(
                signals,
                route.file_path,
                f"route:{route.path}",
                0.55,
                f"Defines authentication route {route.path}",
            )
