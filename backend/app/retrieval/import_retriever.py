import re

from backend.app.retrieval.scoring import SignalMap, add_signal
from backend.app.schemas.intelligence import SymbolIndex

IMPORT_ERROR_PATTERNS = (
    re.compile(r"no module named[ '\"]+([\w.]+)", re.I),
    re.compile(r"cannot import name[ '\"]+([\w]+)", re.I),
    re.compile(r"import(?:ing)?[ '\"]+([\w.]+)", re.I),
)


def add_import_signals(
    issue_text: str, symbol_index: SymbolIndex, signals: SignalMap
) -> None:
    terms = _import_terms(issue_text)
    if not terms:
        return

    for file_symbols in symbol_index.files:
        for imported in file_symbols.imports:
            candidates = {
                imported.module.lower(),
                imported.module.lower().split(".")[-1],
            }
            if imported.name:
                candidates.add(imported.name.lower())
            for term in sorted(terms & candidates):
                add_signal(
                    signals,
                    file_symbols.path,
                    f"import:{term}",
                    0.45,
                    f"Imports matching module or name '{term}'",
                )


def _import_terms(issue_text: str) -> set[str]:
    terms: set[str] = set()
    for pattern in IMPORT_ERROR_PATTERNS:
        terms.update(match.lower() for match in pattern.findall(issue_text))
    return terms
