import subprocess
from pathlib import Path

from backend.app.core.errors import RepositoryError


def clone_repository(repo_url: str, destination: str | Path, branch: str | None = None) -> None:
    command = ["git", "clone"]
    if branch:
        command.extend(["--branch", branch])
    command.extend([repo_url, str(destination)])

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        message = "Failed to clone repository"
        details = {"repo_url": repo_url}
        if isinstance(exc, subprocess.CalledProcessError):
            details["stderr"] = exc.stderr
        raise RepositoryError(message, details=details) from exc
