import json
import tempfile
import unittest
from pathlib import Path

from core.edge_profiles import discover_profiles, prepare_profile, profile_labels


class EdgeProfileTests(unittest.TestCase):
    def test_discovers_missing_profile_and_sorts_numerically(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, bot = Path(tmp) / "edge", Path(tmp) / "bot"
            for root, names in ((source, ["Default", "Profile 2", "Profile 10"]),
                                (bot, ["Default", "Profile 1", "Cache"])):
                for name in names:
                    (root / name).mkdir(parents=True)
                    (root / name / "Preferences").write_text("{}")
            self.assertEqual(discover_profiles(bot, source),
                             ["Default", "Profile 1", "Profile 2", "Profile 10"])

    def test_import_preserves_existing_profile_and_rejects_locked_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, bot = Path(tmp) / "edge", Path(tmp) / "bot"
            (source / "Profile 2").mkdir(parents=True)
            (source / "Profile 2" / "Preferences").write_text('{"test":1}')
            (source / "SingletonLock").symlink_to("test-lock")
            with self.assertRaises(RuntimeError):
                prepare_profile("Profile 2", source, bot)
            self.assertFalse((bot / "Profile 2").exists())
            (source / "SingletonLock").unlink()
            self.assertTrue(prepare_profile("Profile 2", source, bot))
            target = bot / "Profile 2" / "Preferences"
            self.assertEqual(target.read_text(), '{"test":1}')
            target.write_text('{"test":2}')
            self.assertFalse(prepare_profile("Profile 2", source, bot))
            self.assertEqual(target.read_text(), '{"test":2}')
            with self.assertRaises(ValueError):
                prepare_profile("../other", source, bot)

    def test_labels_show_profile_name_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Local State").write_text(json.dumps({"profile": {
                "info_cache": {"Profile 2": {"name": "Personal"}}
            }}))
            self.assertEqual(profile_labels(root), {"Profile 2": "Personal 1"})
