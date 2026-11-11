from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2


class _AtomicJsonStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self._lock = threading.RLock()

    @staticmethod
    def today() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _read_raw(self) -> dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _write_atomic(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass

    def clear(self) -> None:
        with self._lock:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


class WebProgressStore(_AtomicJsonStore):
    """Daily checkpoint store for PC/Mobile/Daily stages.

    Reads the old v5.2 flat schema and migrates it in memory automatically.
    """

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "date": self.today(),
            "profiles": {},
            "updated_at": self.now(),
        }

    def _migrate(self, raw: dict[str, Any]) -> dict[str, Any]:
        if raw.get("schema_version") == SCHEMA_VERSION and isinstance(raw.get("profiles"), dict):
            return raw

        # v5.2: {acc, mode, index, last_points, date}
        if raw.get("acc") and raw.get("mode"):
            doc = self._empty()
            acc = str(raw["acc"])
            mode = str(raw["mode"])
            doc["date"] = str(raw.get("date") or self.today())
            doc["profiles"][acc] = {
                "status": "RUNNING",
                "stages": {
                    mode: {
                        "status": "RUNNING",
                        "index": int(raw.get("index", 0) or 0),
                        "last_points": raw.get("last_points", "N/A"),
                        "updated_at": self.now(),
                    }
                },
            }
            return doc
        return self._empty()

    def load(self) -> dict[str, Any]:
        with self._lock:
            raw = self._read_raw()
            doc = self._migrate(raw)
            if doc.get("date") != self.today():
                doc = self._empty()
                self._write_atomic(doc)
            elif raw and raw != doc:
                self._write_atomic(doc)
            return doc

    def _save(self, doc: dict[str, Any]) -> None:
        doc["schema_version"] = SCHEMA_VERSION
        doc["date"] = self.today()
        doc["updated_at"] = self.now()
        self._write_atomic(doc)

    def get_stage(self, account: str, stage: str) -> dict[str, Any]:
        doc = self.load()
        return dict(doc.get("profiles", {}).get(account, {}).get("stages", {}).get(stage, {}))

    def save_stage(self, account: str, stage: str, index: int, last_points: Any, status: str = "RUNNING") -> None:
        with self._lock:
            doc = self.load()
            profile = doc["profiles"].setdefault(account, {"status": "RUNNING", "stages": {}})
            profile["status"] = "RUNNING"
            profile.setdefault("stages", {})[stage] = {
                "status": status,
                "index": int(index),
                "last_points": last_points,
                "updated_at": self.now(),
            }
            self._save(doc)

    def mark_stage_completed(self, account: str, stage: str, index: int, last_points: Any = "N/A") -> None:
        self.save_stage(account, stage, index, last_points, status="SUCCESS")

    def is_stage_completed(self, account: str, stage: str) -> bool:
        return self.get_stage(account, stage).get("status") == "SUCCESS"

    def mark_profile_completed(self, account: str) -> None:
        with self._lock:
            doc = self.load()
            profile = doc["profiles"].setdefault(account, {"status": "RUNNING", "stages": {}})
            profile["status"] = "SUCCESS"
            profile["updated_at"] = self.now()
            self._save(doc)

    def is_profile_completed(self, account: str) -> bool:
        doc = self.load()
        return doc.get("profiles", {}).get(account, {}).get("status") == "SUCCESS"

    def clear_profile(self, account: str) -> None:
        with self._lock:
            doc = self.load()
            doc.get("profiles", {}).pop(account, None)
            self._save(doc)

    def first_incomplete_index(self, accounts: list[str]) -> int:
        for index, account in enumerate(accounts):
            if not self.is_profile_completed(account):
                return index
        return len(accounts)


class DashboardProgressStore(WebProgressStore):
    """Keep today's stage results independently of resumable checkpoints."""

    def merge_profiles(self, profiles: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            doc = self.load()
            changed = False
            for account, profile in profiles.items():
                saved = doc["profiles"].setdefault(account, {"stages": {}})
                for stage, result in profile.get("stages", {}).items():
                    if saved["stages"].get(stage) != result:
                        saved["stages"][stage] = dict(result)
                        changed = True
            if changed:
                self._save(doc)
            return doc


class WaydroidProgressStore(_AtomicJsonStore):
    """Daily per-profile progress with backward compatibility for v5.2."""

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "date": self.today(),
            "profiles": {},
            "updated_at": self.now(),
        }

    def _migrate(self, raw: dict[str, Any]) -> dict[str, Any]:
        if raw.get("schema_version") == SCHEMA_VERSION and isinstance(raw.get("profiles"), dict):
            return raw

        # v5.2 Waydroid: {"Profile X": {"status":"DONE", "date":"YYYY-MM-DD"}}
        legacy_profiles: dict[str, Any] = {}
        legacy_date = ""
        for key, value in raw.items():
            if isinstance(value, dict) and "status" in value:
                entry_date = str(value.get("date") or "")
                if not legacy_date:
                    legacy_date = entry_date
                legacy_profiles[key] = {
                    "status": value.get("status", "PENDING"),
                    "updated_at": self.now(),
                }
        if legacy_profiles:
            doc = self._empty()
            doc["date"] = legacy_date or self.today()
            doc["profiles"] = legacy_profiles
            return doc
        return self._empty()

    def load(self) -> dict[str, Any]:
        with self._lock:
            raw = self._read_raw()
            doc = self._migrate(raw)
            if doc.get("date") != self.today():
                doc = self._empty()
                self._write_atomic(doc)
            elif raw and raw != doc:
                self._write_atomic(doc)
            return doc

    def status(self, account: str) -> str:
        return str(self.load().get("profiles", {}).get(account, {}).get("status", "PENDING"))

    def set_status(self, account: str, status: str) -> None:
        with self._lock:
            doc = self.load()
            doc["profiles"][account] = {"status": status, "updated_at": self.now()}
            doc["updated_at"] = self.now()
            self._write_atomic(doc)
