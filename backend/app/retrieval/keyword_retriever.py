import re
from pathlib import PurePosixPath

from backend.app.retrieval.scoring import SignalMap, add_signal
from backend.app.schemas.intelligence import PythonFileSymbols, SymbolIndex

WORD_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
FILE_PATTERN = re.compile(r"\b[\w./\\-]+\.(?:py|toml|ini|cfg|yaml|yml|json)\b", re.I)
USEFUL_KEYWORDS = {
    "cors",
    "middleware",
    "config",
    "import",
    "database",
    "db",
    "settings",
}


def add_keyword_signals(
    issue_text: str,
    file_paths: list[str],
    symbol_index: SymbolIndex,
    signals: SignalMap,
) -> None:
    issue = issue_text.lower()
    words = set(WORD_PATTERN.findall(issue))
    mentioned_files = {
        PurePosixPath(match.replace("\\", "/")).name.lower()
        for match in FILE_PATTERN.findall(issue_text)
    }

    for file_path in file_paths:
        name = PurePosixPath(file_path).name.lower()
        stem = PurePosixPath(file_path).stem.lower()
        path_words = set(WORD_PATTERN.findall(file_path.lower()))
        if name in mentioned_files:
            add_signal(
                signals, file_path, f"file:{name}", 0.55, f"Issue mentions {name}"
            )
        if stem in words:
            add_signal(
                signals,
                file_path,
                f"filename:{stem}",
                0.28,
                f"Filename matches '{stem}'",
            )
        for keyword in sorted(words & USEFUL_KEYWORDS & path_words):
            add_signal(
                signals,
                file_path,
                f"keyword:{keyword}",
                0.20,
                f"File path matches issue keyword '{keyword}'",
            )

    if "cors" in words:
        priorities = {
            "main.py": 0.40,
            "app.py": 0.38,
            "config.py": 0.36,
            "settings.py": 0.34,
        }
        for file_path in file_paths:
            name = PurePosixPath(file_path).name.lower()
            if name in priorities:
                add_signal(
                    signals,
                    file_path,
                    "keyword:cors",
                    priorities[name],
                    "Likely CORS configuration file",
                )

    if words & {"login", "auth", "authentication", "authorization"}:
        priorities = {
            "auth.py": 0.38,
            "login.py": 0.36,
            "user.py": 0.28,
            "users.py": 0.26,
        }
        for file_path in file_paths:
            name = PurePosixPath(file_path).name.lower()
            if name in priorities:
                add_signal(
                    signals,
                    file_path,
                    "keyword:auth",
                    priorities[name],
                    "Likely authentication file",
                )

    matched_keywords = words & USEFUL_KEYWORDS
    for file_symbols in symbol_index.files:
        symbol_words = _symbol_words(file_symbols)
        for keyword in sorted(matched_keywords & symbol_words):
            add_signal(
                signals,
                file_symbols.path,
                f"keyword:{keyword}",
                0.18,
                f"Symbols match issue keyword '{keyword}'",
            )


def _symbol_words(file_symbols: PythonFileSymbols) -> set[str]:
    values: list[str] = []
    for function in file_symbols.functions:
        values.append(function.name)
    for class_info in file_symbols.classes:
        values.append(class_info.name)
        values.extend(method.name for method in class_info.methods)
    for imported in file_symbols.imports:
        values.extend((imported.module, imported.name or ""))
    return {word.lower() for value in values for word in WORD_PATTERN.findall(value)}
