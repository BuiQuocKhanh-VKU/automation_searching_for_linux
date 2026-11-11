import threading
import time
import unittest

from core.runtime import CancelledError, RuntimeControl


class RuntimeControlTests(unittest.TestCase):
    def test_wait_is_interruptible(self):
        stop = threading.Event()
        runtime = RuntimeControl(stop, lambda _: None)
        stop.set()
        started = time.monotonic()
        with self.assertRaises(CancelledError):
            runtime.sleep(30)
        self.assertLess(time.monotonic() - started, 0.5)


if __name__ == "__main__":
    unittest.main()
