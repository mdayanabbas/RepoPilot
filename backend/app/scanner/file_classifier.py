from pathlib import Path

from backend.app.schemas.scan import FileType

CONFIG_FILE_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
    "mypy.ini",
    "ruff.toml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}

CONFIG_EXTENSIONS = {
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
}

MARKDOWN_EXTENSIONS = {".md", ".mdx"}
YAML_EXTENSIONS = {".yaml", ".yml"}
TEXT_EXTENSIONS = {".txt"}
ENV_FILE_NAMES = {".env"}


def classify_file(path: str | Path) -> FileType:
    candidate = Path(path)
    name = candidate.name
    lower_name = name.lower()
    suffix = candidate.suffix.lower()

    if suffix == ".py" and (lower_name.startswith("test_") or lower_name.endswith("_test.py")):
        return FileType.test
    if suffix == ".py":
        return FileType.python
    if lower_name in ENV_FILE_NAMES or lower_name.startswith(".env."):
        return FileType.env
    if name in CONFIG_FILE_NAMES or lower_name in CONFIG_FILE_NAMES or suffix in CONFIG_EXTENSIONS:
        return FileType.config
    if suffix in MARKDOWN_EXTENSIONS:
        return FileType.markdown
    if suffix == ".json":
        return FileType.json
    if suffix in YAML_EXTENSIONS:
        return FileType.yaml
    if suffix in TEXT_EXTENSIONS:
        return FileType.text
    return FileType.unknown
