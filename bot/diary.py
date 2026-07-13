"""Append-only server diary for player-facing operational history."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class DiaryEntry:
    """One small server-life event."""

    timestamp: str
    category: str
    message: str
    actorId: int | None = None


class Diary:
    """Write and read a lightweight JSONL diary."""

    def __init__(self, stateDir: str):
        self.stateDir = Path(stateDir)
        self.path = self.stateDir / "server-diary.jsonl"

    def record(self, category: str, message: str, actorId: int | None = None):
        self.stateDir.mkdir(parents=True, exist_ok=True)
        entry = DiaryEntry(
            datetime.now(timezone.utc).isoformat(), category, message[:1000], actorId
        )
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def recent(self, limit: int = 10) -> list[DiaryEntry]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        entries = []
        for line in lines:
            try:
                entries.append(DiaryEntry(**json.loads(line)))
            except (TypeError, json.JSONDecodeError):
                continue
        return list(reversed(entries))
