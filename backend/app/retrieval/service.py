from pathlib import PurePosixPath

from backend.app.retrieval.git_retriever import add_git_signals
from backend.app.retrieval.import_retriever import add_import_signals
from backend.app.retrieval.keyword_retriever import add_keyword_signals
from backend.app.retrieval.route_retriever import add_route_signals
from backend.app.retrieval.scoring import SignalMap, add_signal, score_files
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.retrieval import RetrievalInput, RetrievalResult
from backend.app.schemas.scan import FileType


class RetrievalService:
    def retrieve(self, retrieval_input: RetrievalInput) -> RetrievalResult:
        candidate_files = [
            file
            for file in retrieval_input.scanned_files
            if file.file_type in {FileType.python, FileType.test, FileType.config}
        ]
        file_paths = [file.path for file in candidate_files]
        signals: SignalMap = {}

        for scanned_file in candidate_files:
            base_weight = (
                0.08
                if scanned_file.file_type in {FileType.python, FileType.test}
                else 0.04
            )
            add_signal(
                signals,
                scanned_file.path,
                "file:type",
                base_weight,
                "Relevant source or configuration file",
            )

        _add_framework_signals(retrieval_input, file_paths, signals)
        add_keyword_signals(
            retrieval_input.issue_text,
            file_paths,
            retrieval_input.symbol_index,
            signals,
        )
        add_route_signals(
            retrieval_input.issue_text, retrieval_input.route_index, signals
        )
        add_import_signals(
            retrieval_input.issue_text, retrieval_input.symbol_index, signals
        )
        add_git_signals(retrieval_input, file_paths, signals)
        candidate_path_set = set(file_paths)
        signals = {
            path: values
            for path, values in signals.items()
            if path in candidate_path_set
        }
        return RetrievalResult(files=score_files(signals, retrieval_input.top_n))


def _add_framework_signals(
    retrieval_input: RetrievalInput,
    file_paths: list[str],
    signals: SignalMap,
) -> None:
    preferred_name = {
        SupportedFramework.fastapi: "main.py",
        SupportedFramework.flask: "app.py",
    }.get(retrieval_input.framework)
    if preferred_name:
        for file_path in file_paths:
            if PurePosixPath(file_path).name.lower() == preferred_name:
                add_signal(
                    signals,
                    file_path,
                    f"framework:{retrieval_input.framework.value}",
                    0.20,
                    f"Likely {retrieval_input.framework.value} application setup",
                )

    framework_module = retrieval_input.framework.value
    for file_symbols in retrieval_input.symbol_index.files:
        if any(
            imported.module.lstrip(".").lower() == framework_module
            for imported in file_symbols.imports
        ):
            add_signal(
                signals,
                file_symbols.path,
                f"import:{framework_module}",
                0.14,
                f"Imports the detected {framework_module} framework",
            )


def retrieve_relevant_files(retrieval_input: RetrievalInput) -> RetrievalResult:
    return RetrievalService().retrieve(retrieval_input)
