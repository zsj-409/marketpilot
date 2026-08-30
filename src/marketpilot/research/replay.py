"""Strict, deterministic replay store."""

import json
from pathlib import Path

from marketpilot.research.canonicalization import request_hash
from marketpilot.research.errors import ReplayMissError


class ReplayStore:
    """Record and look up research responses by stable request key."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, object]] = {}

    def record(self, request_key: str, payload: dict[str, object]) -> None:
        self._records[request_key] = payload

    def lookup(self, request_key: str) -> dict[str, object]:
        try:
            return self._records[request_key]
        except KeyError as exc:
            raise ReplayMissError(f"replay miss for request key: {request_key}") from exc

    @staticmethod
    def key(parts: list[str]) -> str:
        return request_hash(parts)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for key, payload in sorted(self._records.items()):
                handle.write(
                    json.dumps({"request_key": key, "payload": payload}, ensure_ascii=False) + "\n"
                )

    def load(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = json.loads(line)
                self._records[str(item["request_key"])] = dict(item["payload"])
