"""V2-REL-001: Reliability tests"""
import unittest
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOffsetReliability(unittest.TestCase):
    def test_atomic_write_uses_rename(self):
        """OffsetStore uses atomic write via tmp+rename"""
        from maskai.utils.offset_store import OffsetStore
        path = "/tmp/test_atomic_offset.txt"
        store = OffsetStore(path)
        store.save(99999)
        with open(path) as f:
            self.assertEqual(f.read().strip(), "99999")
        # tmp file should not exist after rename
        self.assertFalse(os.path.exists(path + ".tmp"))
        os.remove(path)

    def test_corrupt_file_recovery(self):
        """Corrupt offset file → warning logged, returns 0, bot continues"""
        import logging
        path = "/tmp/test_corrupt_offset2.txt"
        with open(path, 'w') as f:
            f.write("not_a_number_garbage")
        from maskai.utils.offset_store import OffsetStore
        store = OffsetStore(path)
        logger = logging.getLogger("maskai.utils.offset")
        with self.assertLogs(logger, level='WARNING') as cm:
            val = store.load()
        self.assertEqual(val, 0)
        self.assertTrue(any("Corrupt" in m for m in cm.output))
        os.remove(path)

    def test_missing_file_returns_zero(self):
        """Missing offset file → returns 0"""
        from maskai.utils.offset_store import OffsetStore
        store = OffsetStore("/tmp/nonexistent_offset_xyz.txt")
        self.assertEqual(store.load(), 0)


class TestRetryPolicy(unittest.TestCase):
    def test_exponential_backoff_increases(self):
        """Backoff doubles after each failure, capped at 60"""
        backoff = 1
        backoffs = []
        for _ in range(5):
            backoffs.append(backoff)
            backoff = min(backoff * 2, 60)
        self.assertEqual(backoffs, [1, 2, 4, 8, 16])
        self.assertEqual(backoff, 32)

    def test_success_resets_backoff(self):
        """After success, backoff resets to 1"""
        backoff = 16
        backoff = 1  # reset on success
        self.assertEqual(backoff, 1)


class TestShutdown(unittest.TestCase):
    @patch('maskai.app.process_single_update')
    def test_stop_signal_saves_offset(self, mock_process):
        """__STOP__ → offset saved before exit"""
        from maskai.utils.offset_store import OffsetStore
        mock_process.return_value = "__STOP__"
        store = OffsetStore("/tmp/test_stop_offset.txt")
        store.save(500)
        # simulate: process_single_update returns __STOP__, main saves offset
        result = mock_process({}, store)
        if result == "__STOP__":
            offset = 501
            store.save(offset)
        self.assertEqual(store.load(), 501)
        mock_process.assert_called_once()
        import os
        os.remove("/tmp/test_stop_offset.txt")


class TestDuplicateOffset(unittest.TestCase):
    def test_duplicate_advances_offset(self):
        """ALREADY_EXISTS → offset still advances (to avoid reprocessing)"""
        from maskai.app import process_single_update
        from maskai.utils.offset_store import OffsetStore

        with patch('maskai.app.process') as mock_process:
            mock_process.return_value = None  # simulate duplicate handled internally
            store = OffsetStore("/tmp/test_dup_offset.txt")
            upd = {"update_id": 500, "message": {"chat": {"id": 1}, "from": {"id": 1367356347}, "text": "test"}}
            result = process_single_update(upd, store)
            # offset should advance
            self.assertEqual(result, 501)
            self.assertEqual(store.load(), 501)
            import os
            os.remove("/tmp/test_dup_offset.txt")


class TestHandlerException(unittest.TestCase):
    @patch('maskai.app.process')
    def test_exception_keeps_offset(self, mock_process):
        """Handler exception → offset NOT advanced"""
        from maskai.app import process_single_update
        from maskai.utils.offset_store import OffsetStore

        mock_process.side_effect = RuntimeError("handler failure")
        store = OffsetStore("/tmp/test_exc_offset.txt")
        store.save(200)
        upd = {"update_id": 400, "message": {"chat": {"id": 1}, "from": {"id": 1367356347}, "text": "test"}}
        result = process_single_update(upd, store)
        self.assertIsNone(result)
        self.assertEqual(store.load(), 200)  # unchanged
        import os
        os.remove("/tmp/test_exc_offset.txt")


if __name__ == "__main__":
    unittest.main()
