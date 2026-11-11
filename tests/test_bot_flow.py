import threading
import unittest
from unittest.mock import MagicMock, call, patch

from core.bot_logic import BotLogic
from core.models import JobResult


class BotFlowTests(unittest.TestCase):
    def setUp(self):
        self.bot = BotLogic(lambda _: None, threading.Event())
        self.bot.progress = MagicMock()
        self.bot._run_web_stage = MagicMock(return_value=JobResult.success())

    def test_full_run_only_searches_pc_then_mobile(self):
        # Search stages are mocked: opening any additional browser would mean
        # that a removed task still runs between the two search stages.
        with patch('core.bot_logic.setup_edge_driver', side_effect=AssertionError('Unexpected browser task')):
            result = self.bot.run_bot_safe('Default')
        self.assertTrue(result.ok)
        self.assertEqual(self.bot._run_web_stage.call_args_list, [
            call('Default', 'PC', 35), call('Default', 'MOBILE', 25),
        ])
        self.bot.progress.mark_profile_completed.assert_called_once_with('Default')

    def test_mobile_only_does_not_run_pc(self):
        self.bot.run_bot_safe('Profile 2', run_pc=False)
        self.bot._run_web_stage.assert_called_once_with('Profile 2', 'MOBILE', 25)

    def test_pc_failure_does_not_mark_profile_completed(self):
        self.bot._run_web_stage.return_value = JobResult.failed('Default', 'PC', 'Test failure')
        result = self.bot.run_bot_safe('Default')
        self.assertFalse(result.ok)
        self.bot.progress.mark_profile_completed.assert_not_called()
        self.bot._run_web_stage.assert_called_once_with('Default', 'PC', 35)
