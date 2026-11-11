from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path


def discover_profiles(*roots: str | Path) -> list[str]:
    """Read actual Edge profiles, excluding caches and unrelated directories."""
    profiles: set[str] = set()
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for folder in root.iterdir():
            if (folder.name == "Default" or (
                folder.name.startswith("Profile ") and folder.name[8:].isdigit()
            )) and (folder / "Preferences").is_file():
                profiles.add(folder.name)
    return sorted(profiles, key=lambda name: -1 if name == "Default" else int(name[8:]))


def profile_labels(*roots: str | Path) -> dict[str, str]:
    labels: dict[str, str] = {}
    # The bot's own names take precedence when already imported.
    for root in reversed(roots):
        try:
            cache = json.loads((Path(root) / "Local State").read_text(encoding="utf-8"))
            for key, value in cache.get("profile", {}).get("info_cache", {}).items():
                name = value.get("name", "").strip()
                if name:
                    labels[key] = "Personal 1" if name == "Personal" else name
        except (OSError, ValueError, AttributeError):
            continue
    return labels


def prepare_profile(profile: str, source_root: str | Path, bot_root: str | Path) -> bool:
    """Import a missing profile without overwriting an existing bot login."""
    if profile not in discover_profiles(source_root, bot_root):
        raise ValueError(f"Không tìm thấy Edge profile: {profile}")
    source_root, bot_root = Path(source_root), Path(bot_root)
    destination = bot_root / profile
    if (destination / "Preferences").is_file():
        return False
    if destination.exists():
        raise RuntimeError(f"Profile đích chưa đầy đủ; cần kiểm tra: {destination}")
    for root in (source_root, bot_root):
        lock = root / "SingletonLock"
        if lock.exists() or lock.is_symlink():
            raise RuntimeError("Hãy đóng Edge trước khi nhập profile mới vào bot.")
    bot_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".profile-import-", dir=bot_root) as staging:
        staged = Path(staging) / profile
        shutil.copytree(
            source_root / profile,
            staged,
            ignore=shutil.ignore_patterns("Cache", "Code Cache", "GPUCache", "Singleton*"),
        )
        staged.rename(destination)
    return True
