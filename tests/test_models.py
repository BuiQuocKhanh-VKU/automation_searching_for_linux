import unittest

from core.models import RuntimeConfig


class RuntimeConfigTests(unittest.TestCase):
    def test_defaults_match_tested_ui(self):
        cfg = RuntimeConfig()
        self.assertEqual(cfg.pc_count, 35)
        self.assertEqual(cfg.mobile_count, 25)
        self.assertEqual(cfg.check_interval, 3)
        self.assertEqual(cfg.type_min, 0.3)
        self.assertEqual(cfg.type_max, 0.3)
        self.assertEqual(cfg.read_min, 3.0)
        self.assertEqual(cfg.read_max, 4.0)
        self.assertEqual(cfg.think_time, 3.0)

    def test_invalid_interval_rejected(self):
        with self.assertRaises(ValueError):
            RuntimeConfig.from_mapping({"check_interval": 0})

    def test_inverted_ranges_rejected(self):
        with self.assertRaises(ValueError):
            RuntimeConfig.from_mapping({"type_min": 1, "type_max": 0.2})
        with self.assertRaises(ValueError):
            RuntimeConfig.from_mapping({"read_min": 12, "read_max": 8})


if __name__ == "__main__":
    unittest.main()
