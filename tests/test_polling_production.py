"""CR-012: Production polling tests — calls process_single_update()"""
import unittest
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPollingProduction(unittest.TestCase):
    @patch('maskai.app.delete_owned_category')
    @patch('maskai.app.get_accessible_category')
    @patch('maskai.app.send')
    @patch('maskai.app.cmd_kategori')
    def test_callback_advances_offset(self, mock_kategori, mock_send, mock_cat, mock_del):
        """Callback processing → offset_store.save called with next_offset"""
        from maskai.app import process_single_update
        from maskai.utils.offset_store import OffsetStore

        store = OffsetStore("/tmp/test_poll_offset.txt")
        upd = {
            "update_id": 500,
            "callback_query": {
                "from": {"id": 1367356347},
                "data": "menu_kategori",
                "message": {"chat": {"id": 123}}
            }
        }
        result = process_single_update(upd, store)
        self.assertEqual(result, 501)
        self.assertEqual(store.load(), 501)
        import os
        os.remove("/tmp/test_poll_offset.txt")

    @patch('maskai.app.process')
    def test_message_advances_offset(self, mock_process):
        """Message processing → offset advances"""
        from maskai.app import process_single_update
        from maskai.utils.offset_store import OffsetStore

        mock_process.return_value = None
        store = OffsetStore("/tmp/test_poll_offset2.txt")
        upd = {
            "update_id": 300,
            "message": {"chat": {"id": 123}, "from": {"id": 1367356347}, "text": "/saldo"}
        }
        result = process_single_update(upd, store)
        self.assertEqual(result, 301)
        self.assertEqual(store.load(), 301)
        import os
        os.remove("/tmp/test_poll_offset2.txt")

    @patch('maskai.app.process')
    def test_stop_returns_signal(self, mock_process):
        """Handler returns __STOP__ → process_single_update returns __STOP__"""
        from maskai.app import process_single_update
        from maskai.utils.offset_store import OffsetStore

        mock_process.return_value = "__STOP__"
        store = OffsetStore("/tmp/test_poll_stop.txt")
        upd = {
            "update_id": 100,
            "message": {"chat": {"id": 1}, "from": {"id": 1367356347}, "text": "/stop"}
        }
        result = process_single_update(upd, store)
        self.assertEqual(result, "__STOP__")
        self.assertEqual(store.load(), 101)
        import os
        os.remove("/tmp/test_poll_stop.txt")

    @patch('maskai.app.process')
    def test_exception_returns_none_no_advance(self, mock_process):
        """Handler raises exception → offset NOT advanced"""
        from maskai.app import process_single_update
        from maskai.utils.offset_store import OffsetStore

        mock_process.side_effect = RuntimeError("fail")
        store = OffsetStore("/tmp/test_poll_exc.txt")
        store.save(200)
        upd = {
            "update_id": 400,
            "message": {"chat": {"id": 1}, "from": {"id": 1367356347}, "text": "test"}
        }
        result = process_single_update(upd, store)
        self.assertIsNone(result)
        # Offset should NOT have advanced
        self.assertEqual(store.load(), 200)
        import os
        os.remove("/tmp/test_poll_exc.txt")


if __name__ == "__main__":
    unittest.main()
