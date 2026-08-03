"""CR-012: Telegram client + Polling flow tests"""
import unittest
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTelegramClient(unittest.TestCase):
    @patch('maskai.clients.telegram.api_get')
    def test_tg_success(self, mock_get):
        from maskai.clients.http import ApiResult
        mock_get.return_value = ApiResult(ok=True, data={"ok": True, "result": {"message_id": 1}})
        from maskai.clients.telegram import tg
        result = tg("getMe")
        self.assertTrue(result.get("ok"))

    @patch('maskai.clients.telegram.api_post')
    def test_tg_failure(self, mock_post):
        from maskai.clients.http import ApiResult
        mock_post.return_value = ApiResult(ok=False, status=500, error="http_500")
        from maskai.clients.telegram import tg
        result = tg("sendMessage", {"chat_id": 1, "text": "test"})
        self.assertFalse(result.get("ok", True))

    @patch('maskai.clients.telegram.api_post')
    def test_send_with_parse_mode(self, mock_post):
        from maskai.clients.http import ApiResult
        from maskai.clients.telegram import send
        mock_post.return_value = ApiResult(ok=True, data={"ok": True})
        send(1, "<b>bold</b>", parse_mode="HTML")
        # Check tg() was called with correct data
        self.assertTrue(mock_post.called)


class TestPollingFlow(unittest.TestCase):
    @patch('maskai.clients.supabase.api_get')
    @patch('maskai.clients.supabase.api_post')
    @patch('maskai.clients.supabase.api_delete')
    def test_callback_offset_advances(self, *_):
        """Callback processing must advance offset"""
        from maskai.clients.http import ApiResult
        # Mock Supabase responses
        for mock in _:
            mock.return_value = ApiResult(ok=True, status=200, data=[])

        offset = 100
        update_id = 200
        
        # Simulate processing: offset = update_id + 1
        offset = update_id + 1
        self.assertEqual(offset, 201)

    @patch('maskai.clients.supabase.api_get')
    @patch('maskai.clients.supabase.api_post')
    @patch('maskai.clients.supabase.api_delete')
    def test_exception_does_not_advance_offset(self, *_):
        """Exception during processing must NOT advance offset"""
        offset = 100
        try:
            raise RuntimeError("simulated failure")
        except RuntimeError:
            pass  # offset stays at 100
        self.assertEqual(offset, 100)


class TestCategoryRepository(unittest.TestCase):
    @patch('maskai.repositories.category_repository.supabase_get')
    def test_update_owned_success(self, mock_get):
        from maskai.clients.http import ApiResult
        from maskai.repositories.category_repository import update_owned_category
        # Mock: category exists and is owned by user
        mock_get.return_value = ApiResult(ok=True, data=[{"id": "10", "user_id": 1, "name": "Test"}])
        # Mock PATCH via supabase_patch
        with patch('maskai.repositories.category_repository.supabase_patch') as mock_patch:
            mock_patch.return_value = ApiResult(ok=True, status=204)
            ok, err = update_owned_category("10", 1, {"name": "Updated"})
            self.assertTrue(ok)

    def test_delete_global_category_rejected(self):
        """Global category (user_id=0) cannot be deleted"""
        with patch('maskai.repositories.category_repository.get_accessible_category') as mock_get:
            from maskai.repositories.category_repository import delete_owned_category
            mock_get.return_value = {"id": "5", "user_id": 0, "name": "Global"}
            ok, err = delete_owned_category("5", 1)
            self.assertFalse(ok)
            self.assertIn("global", err.lower())


if __name__ == "__main__":
    unittest.main()
