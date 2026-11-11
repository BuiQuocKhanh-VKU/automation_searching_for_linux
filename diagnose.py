from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from config import (
    DRIVER_FILENAME,
    EDGE_USER_DATA_DIR,
    MS_EDGE_BINARY,
    PROFILES_LIST,
    WAYDROID_IP,
)

ROOT = Path(__file__).resolve().parent


def status(ok: bool) -> str:
    return "OK" if ok else "MISSING"


def main() -> int:
    print("MS Automation v6.0 - Environment diagnostics")
    print("=" * 56)
    print(f"Python: {sys.version.split()[0]} ({status(sys.version_info >= (3, 10))})")
    print(f"Edge: {MS_EDGE_BINARY} ({status(Path(MS_EDGE_BINARY).exists())})")
    print(f"Edge user-data: {EDGE_USER_DATA_DIR} ({status(Path(EDGE_USER_DATA_DIR).exists())})")

    local_driver = ROOT / DRIVER_FILENAME
    driver = str(local_driver) if local_driver.exists() else shutil.which(DRIVER_FILENAME)
    print(f"EdgeDriver: {driver or 'Selenium Manager fallback'}")
    print(f"ADB: {shutil.which('adb') or 'MISSING'}")
    print(f"Waydroid: {shutil.which('waydroid') or 'MISSING'}")
    print(f"Waydroid target: {WAYDROID_IP}")

    print("\nProfiles:")
    for profile in PROFILES_LIST:
        p = Path(EDGE_USER_DATA_DIR) / profile
        print(f"  - {profile}: {status(p.exists())} ({p})")

    print("\nProgress JSON:")
    for name in ("bot_progress.json", "waydroid_progress.json"):
        path = ROOT / name
        if not path.exists():
            print(f"  - {name}: chưa có (bình thường trước lần chạy đầu)")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            print(f"  - {name}: JSON hợp lệ")
        except Exception as exc:
            print(f"  - {name}: LỖI JSON: {exc}")

    print("\nGợi ý: nếu msedgedriver không có, Selenium Manager sẽ được dùng.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
