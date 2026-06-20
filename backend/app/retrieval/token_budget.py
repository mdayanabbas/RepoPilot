from dataclasses import dataclass


@dataclass(slots=True)
class CharacterBudget:
    max_file_chars: int
    max_context_chars: int
    used_chars: int = 0

    @property
    def remaining_chars(self) -> int:
        return max(self.max_context_chars - self.used_chars, 0)

    @property
    def next_file_limit(self) -> int:
        return min(self.max_file_chars, self.remaining_chars)

    def add(self, content: str, source_has_more: bool = False) -> tuple[str, bool]:
        limit = self.next_file_limit
        included = content[:limit]
        self.used_chars += len(included)
        truncated = source_has_more or len(content) > limit
        return included, truncated
