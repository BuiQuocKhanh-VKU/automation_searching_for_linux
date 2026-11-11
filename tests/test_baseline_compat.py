import unittest

import config


class BaselineCompatibilityTests(unittest.TestCase):
    def test_configured_runtime_parameters(self):
        self.assertEqual(config.DEFAULT_BOT_CONFIG, {
            "pc_count": 35,
            "mobile_count": 25,
            "check_interval": 3,
            "type_min": 0.3,
            "type_max": 0.3,
            "read_min": 3,
            "read_max": 4,
            "think_time": 3,
        })
        self.assertEqual(config.PROFILE_SWITCH_DELAY, 10)
        self.assertEqual(config.CAPTCHA_WAIT_SECONDS, 90)
        self.assertEqual(config.SHUTDOWN_COUNTDOWN_SECONDS, 60)
        self.assertEqual(config.DRIVER_RETRY_COUNT, 2)

    def test_v52_mobile_and_waydroid_parameters(self):
        self.assertEqual(config.REMOTE_DEBUGGING_PORT, 9222)
        self.assertEqual(config.MOBILE_WINDOW_SIZE, "390,844")
        self.assertIn("iPhone OS 16_6", config.MOBILE_USER_AGENT)
        self.assertEqual(config.MOBILE_PLATFORM, "iPhone")
        self.assertEqual(config.MOBILE_PLATFORM_VERSION, "16.6")
        self.assertEqual(config.WAYDROID_NEWS_COUNT, 15)
        self.assertEqual(
            config.WAYDROID_CHECKIN_X,
            [0.125, 0.243, 0.375, 0.500, 0.628, 0.754, 0.885],
        )
        self.assertEqual(config.WAYDROID_CHECKIN_Y, 0.539)
        self.assertEqual(config.BING_APP_PACKAGE, "com.microsoft.bing")


if __name__ == "__main__":
    unittest.main()
