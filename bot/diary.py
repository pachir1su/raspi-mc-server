"""Append-only server diary with bounded Raspberry Pi disk usage."""

import json
import os
import threading
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class DiaryEntry:
    """One friend or system event in the shared server history."""

    entryId: str
    category: str
    message: str
    authorId: int
    createdAt: str
    imagePath: str | None = None


class DiaryStore:
    """Persist small events as JSONL and compact only when the file grows."""

    def __init__(
        self,
        stateDir: str | Path,
        maxBytes: int = 2 * 1024 * 1024,
        retainedEntries: int = 1000,
    ):
        # JSONL makes normal writes constant-time; compaction is intentionally rare.
        self.stateDir = Path(stateDir)
        self.path = self.stateDir / "server-diary.jsonl"
        self.maxBytes = maxBytes
        self.retainedEntries = retainedEntries
        self.lock = threading.Lock()

    @staticmethod
    def _validate(category: str, message: str) -> tuple[str, str]:
        """Reject multiline categories and oversized or empty messages."""
        cleanedCategory = (category or "note").strip().lower()
        cleanedMessage = (message or "").strip()
        if not cleanedCategory or len(cleanedCategory) > 32 or "\n" in cleanedCategory:
            raise ValueError("Diary category must be 1-32 characters on one line")
        if not cleanedMessage or len(cleanedMessage) > 1000:
            raise ValueError("Diary message must be 1-1000 characters")
        return cleanedCategory, cleanedMessage

    @staticmethod
    def _parse(line: str) -> DiaryEntry | None:
        """Skip one damaged line without losing later valid diary entries."""
        try:
            raw = json.loads(line)
            return DiaryEntry(**raw)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _recentUnlocked(self, limit: int) -> list[DiaryEntry]:
        """Read only a bounded tail while the caller owns the lock."""
        if not self.path.exists():
            return []
        entries: deque[DiaryEntry] = deque(maxlen=max(1, limit))
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                entry = self._parse(line)
                if entry:
                    entries.append(entry)
        return list(reversed(entries))

    def _compactUnlocked(self) -> None:
        """Retain recent events when the append-only file crosses its size cap."""
        if not self.path.exists() or self.path.stat().st_size <= self.maxBytes:
            return
        recentEntries = list(
            reversed(self._recentUnlocked(self.retainedEntries))
        )
        temporaryPath = self.path.with_suffix(".tmp")
        with temporaryPath.open("w", encoding="utf-8") as file:
            for entry in recentEntries:
                file.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporaryPath, self.path)

    def record(
        self,
        category: str,
        message: str,
        authorId: int,
        imagePath: str | None = None,
    ) -> DiaryEntry:
        """Append one entry and return the immutable stored record."""
        cleanedCategory, cleanedMessage = self._validate(category, message)
        entry = DiaryEntry(
            entryId=uuid.uuid4().hex[:12],
            category=cleanedCategory,
            message=cleanedMessage,
            authorId=authorId,
            createdAt=datetime.now(timezone.utc).isoformat(),
            imagePath=imagePath,
        )
        with self.lock:
            self.stateDir.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
                file.flush()
                os.fsync(file.fileno())
            self._compactUnlocked()
        return entry

    def recent(self, limit: int = 10) -> list[DiaryEntry]:
        """Return newest entries first with a hard display bound."""
        safeLimit = min(max(int(limit), 1), 50)
        with self.lock:
            return self._recentUnlocked(safeLimit)

    def get(self, entryId: str) -> DiaryEntry | None:
        """Find one entry within the retained bounded diary."""
        wantedId = (entryId or "").strip().lower()
        if not wantedId:
            return None
        with self.lock:
            entries = self._recentUnlocked(self.retainedEntries)
        return next((entry for entry in entries if entry.entryId == wantedId), None)
