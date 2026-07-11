"""Append-only audit records for privileged Discord operations."""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


class AuditLog:
    """Persist compact JSON lines without exposing tokens or RCON credentials."""

    def __init__(self, stateDir: str):
        self.stateDir = Path(stateDir).resolve()
        self.path = self.stateDir / "audit.jsonl"
        self.writeLock = threading.Lock()

    def record(
        self,
        action: str,
        actorId: int,
        outcome: str,
        detail: str = "",
    ):
        """Append one flushed record so abrupt power loss loses at most one line."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actorId": actorId,
            "outcome": outcome,
            "detail": detail[:500],
        }
        self.stateDir.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with self.writeLock:
            with self.path.open("a", encoding="utf-8") as auditFile:
                auditFile.write(encoded + "\n")
                auditFile.flush()
                os.fsync(auditFile.fileno())

    def recent(self, limit: int = 20) -> list[dict]:
        """Return the newest valid records while tolerating a truncated last line."""
        if not self.path.exists():
            return []
        records = []
        with self.path.open("r", encoding="utf-8") as auditFile:
            for line in auditFile:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records[-max(1, min(limit, 100)):][::-1]
