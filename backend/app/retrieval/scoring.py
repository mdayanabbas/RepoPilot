from dataclasses import dataclass

from backend.app.schemas.retrieval import RelevantFile


@dataclass(frozen=True, slots=True)
class ScoreSignal:
    name: str
    weight: float
    reason: str


SignalMap = dict[str, list[ScoreSignal]]


def add_signal(
    signals: SignalMap,
    file_path: str,
    name: str,
    weight: float,
    reason: str,
) -> None:
    file_signals = signals.setdefault(file_path, [])
    if any(signal.name == name for signal in file_signals):
        return
    file_signals.append(ScoreSignal(name=name, weight=weight, reason=reason))


def score_files(signals: SignalMap, top_n: int = 6) -> list[RelevantFile]:
    scored = [
        RelevantFile(
            file_path=file_path,
            score=round(min(sum(signal.weight for signal in file_signals), 1.0), 4),
            reason="; ".join(signal.reason for signal in file_signals),
            matched_signals=[signal.name for signal in file_signals],
        )
        for file_path, file_signals in signals.items()
        if file_signals
    ]
    return sorted(scored, key=lambda item: (-item.score, item.file_path))[:top_n]
