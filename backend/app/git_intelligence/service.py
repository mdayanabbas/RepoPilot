from pathlib import Path

from backend.app.git_intelligence.change_frequency import calculate_change_frequency
from backend.app.git_intelligence.git_blame_analyzer import get_file_blame
from backend.app.git_intelligence.git_log_analyzer import get_recent_commits
from backend.app.schemas.git_intelligence import GitHistoryResult


class GitIntelligenceService:
    def analyze_repository(
        self,
        repo_path: str | Path,
        *,
        limit: int = 20,
        blame_file_path: str | None = None,
    ) -> GitHistoryResult:
        return GitHistoryResult(
            recent_commits=get_recent_commits(repo_path, limit),
            change_frequency=calculate_change_frequency(repo_path),
            blame=get_file_blame(repo_path, blame_file_path),
        )
