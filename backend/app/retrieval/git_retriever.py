import re

from backend.app.retrieval.scoring import SignalMap, add_signal
from backend.app.schemas.git_intelligence import GitCommitInfo, GitHistoryResult
from backend.app.schemas.retrieval import RetrievalInput

WORD_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
MAX_RECENT_COMMITS = 5
RECENT_WEIGHT = 0.08
HIGH_CHURN_WEIGHT = 0.10
MESSAGE_MATCH_WEIGHT = 0.14
RELATED_FILE_WEIGHT = 0.08


def add_git_signals(
    retrieval_input: RetrievalInput,
    file_paths: list[str],
    signals: SignalMap,
) -> None:
    git_history = retrieval_input.git_history
    if git_history is None:
        return

    candidate_paths = set(file_paths)
    if not candidate_paths:
        return

    _add_recent_change_signals(git_history, candidate_paths, signals)
    _add_high_churn_signals(git_history, candidate_paths, signals)
    _add_commit_message_signals(
        retrieval_input.issue_text,
        git_history,
        candidate_paths,
        signals,
    )
    _add_related_file_signals(retrieval_input, git_history, candidate_paths, signals)


def _add_recent_change_signals(
    git_history: GitHistoryResult,
    candidate_paths: set[str],
    signals: SignalMap,
) -> None:
    recent_paths: set[str] = set()
    for commit in git_history.recent_commits[:MAX_RECENT_COMMITS]:
        recent_paths.update(
            path for path in commit.changed_files if path in candidate_paths
        )

    for file_path in sorted(recent_paths):
        add_signal(
            signals,
            file_path,
            "recently_changed",
            RECENT_WEIGHT,
            "File changed in recent Git history",
        )


def _add_high_churn_signals(
    git_history: GitHistoryResult,
    candidate_paths: set[str],
    signals: SignalMap,
) -> None:
    if not git_history.change_frequency:
        return
    max_count = max(item.commit_count for item in git_history.change_frequency)
    if max_count <= 1:
        return

    threshold = max(2, max_count)
    for item in git_history.change_frequency:
        if item.file_path not in candidate_paths or item.commit_count < threshold:
            continue
        add_signal(
            signals,
            item.file_path,
            "high_change_frequency",
            HIGH_CHURN_WEIGHT,
            "File has high Git change frequency",
        )


def _add_commit_message_signals(
    issue_text: str,
    git_history: GitHistoryResult,
    candidate_paths: set[str],
    signals: SignalMap,
) -> None:
    issue_words = _useful_words(issue_text)
    if not issue_words:
        return

    for commit in git_history.recent_commits:
        if not _commit_matches_issue(commit, issue_words):
            continue
        for file_path in sorted(set(commit.changed_files) & candidate_paths):
            add_signal(
                signals,
                file_path,
                "commit_message_match",
                MESSAGE_MATCH_WEIGHT,
                "Recent commit message matches issue text",
            )


def _add_related_file_signals(
    retrieval_input: RetrievalInput,
    git_history: GitHistoryResult,
    candidate_paths: set[str],
    signals: SignalMap,
) -> None:
    anchor_paths = {
        route.file_path
        for route in retrieval_input.route_index.routes
        if route.file_path in candidate_paths
    }
    anchor_paths.update(
        symbols.path
        for symbols in retrieval_input.symbol_index.files
        if symbols.path in candidate_paths
    )
    if not anchor_paths:
        return

    related_paths: set[str] = set()
    for commit in git_history.recent_commits:
        changed = set(commit.changed_files)
        if not (changed & anchor_paths):
            continue
        related_paths.update(changed & candidate_paths)
    related_paths.difference_update(anchor_paths)

    for file_path in sorted(related_paths):
        add_signal(
            signals,
            file_path,
            "git_related_file",
            RELATED_FILE_WEIGHT,
            "File changed with route or symbol files in Git history",
        )


def _commit_matches_issue(commit: GitCommitInfo, issue_words: set[str]) -> bool:
    message_words = _useful_words(commit.message)
    return bool(issue_words & message_words)


def _useful_words(text: str) -> set[str]:
    return {
        word.lower()
        for word in WORD_PATTERN.findall(text)
        if len(word) >= 3
    }
