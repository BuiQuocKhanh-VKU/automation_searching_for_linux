import json
import tempfile
import unittest
from pathlib import Path

from core.progress_store import DashboardProgressStore, WebProgressStore, WaydroidProgressStore


class ProgressStoreTests(unittest.TestCase):
    def test_web_legacy_progress_migrates_and_resumes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bot_progress.json"
            store = WebProgressStore(str(path))
            path.write_text(
                json.dumps(
                    {
                        "acc": "Profile 2",
                        "mode": "PC",
                        "index": 11,
                        "last_points": "1234",
                        "date": store.today(),
                    }
                ),
                encoding="utf-8",
            )
            stage = store.get_stage("Profile 2", "PC")
            self.assertEqual(stage["index"], 11)
            self.assertEqual(stage["last_points"], "1234")

    def test_waydroid_v52_schema_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "waydroid_progress.json"
            store = WaydroidProgressStore(str(path))
            path.write_text(
                json.dumps({"Profile 5": {"status": "DONE", "date": store.today()}}),
                encoding="utf-8",
            )
            self.assertEqual(store.status("Profile 5"), "DONE")
            migrated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(migrated["schema_version"], 2)
            self.assertEqual(migrated["profiles"]["Profile 5"]["status"], "DONE")

    def test_stage_and_profile_completion(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bot_progress.json"
            store = WebProgressStore(str(path))
            store.save_stage("Profile 2", "PC", 4, "100")
            self.assertFalse(store.is_stage_completed("Profile 2", "PC"))
            store.mark_stage_completed("Profile 2", "PC", 35, "150")
            self.assertTrue(store.is_stage_completed("Profile 2", "PC"))
            store.mark_profile_completed("Profile 2")
            self.assertTrue(store.is_profile_completed("Profile 2"))

    def test_corrupted_json_recovers(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bot_progress.json"
            path.write_text("{bad json", encoding="utf-8")
            store = WebProgressStore(str(path))
            doc = store.load()
            self.assertEqual(doc["profiles"], {})

    def test_dashboard_keeps_results_after_checkpoint_cleanup_and_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            checkpoint = WebProgressStore(str(Path(td) / "checkpoint.json"))
            path = Path(td) / "dashboard.json"
            dashboard = DashboardProgressStore(str(path))
            checkpoint.mark_stage_completed("Profile 2", "MOBILE", 25)
            dashboard.merge_profiles(checkpoint.load()["profiles"])
            checkpoint.clear_profile("Profile 2")
            dashboard.merge_profiles(checkpoint.load()["profiles"])
            self.assertTrue(DashboardProgressStore(str(path)).is_stage_completed("Profile 2", "MOBILE"))

    def test_mobile_only_run_keeps_previous_pc_and_daily_results(self):
        with tempfile.TemporaryDirectory() as td:
            dashboard = DashboardProgressStore(str(Path(td) / "dashboard.json"))
            dashboard.merge_profiles({"Default": {"stages": {
                "PC": {"status": "SUCCESS"}, "DAILY": {"status": "FAILED"}
            }}})
            result = dashboard.merge_profiles({"Default": {"stages": {
                "MOBILE": {"status": "SUCCESS"}
            }}})
            stages = result["profiles"]["Default"]["stages"]
            self.assertEqual(stages["PC"]["status"], "SUCCESS")
            self.assertEqual(stages["DAILY"]["status"], "FAILED")
            self.assertEqual(stages["MOBILE"]["status"], "SUCCESS")

    def test_dashboard_resets_on_new_day(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "dashboard.json"
            dashboard = DashboardProgressStore(str(path))
            dashboard.merge_profiles({"Default": {"stages": {"PC": {"status": "SUCCESS"}}}})
            doc = json.loads(path.read_text())
            doc["date"] = "2000-01-01"
            path.write_text(json.dumps(doc))
            self.assertEqual(dashboard.merge_profiles({})["profiles"], {})


if __name__ == "__main__":
    unittest.main()
