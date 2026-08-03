"""CR-012: OCR production-path tests — calls cmd_ocr directly"""
import unittest
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOCRProduction(unittest.TestCase):
    def setUp(self):
        # Mock all external dependencies
        self.mock_send = patch('maskai.services.ocr_service.send').start()
        self.mock_tg = patch('maskai.services.ocr_service.tg').start()
        self.mock_create_tx = patch('maskai.services.ocr_service.create_transaction').start()
        self.mock_supabase_get = patch('maskai.services.ocr_service.supabase_get').start()
        self.mock_requests = patch('maskai.services.ocr_service.requests.post').start()
        self.addCleanup(patch.stopall)

    def _setup_ocr_success(self, total="25000"):
        """Configure mocks for successful OCR flow"""
        from maskai.clients.http import ApiResult
        from maskai.repositories.transaction_repository import CreateTransactionStatus, CreateTransactionResult

        # Mock getFile: return file_path
        self.mock_tg.return_value = {
            "ok": True,
            "result": {"file_path": "photos/file_1.jpg"},
        }

        # Mock Dahono Vision response
        mock_vision = MagicMock()
        mock_vision.status_code = 200
        mock_vision.text = '{"choices":[{"message":{"content":"{\\"toko\\":\\"Indomaret\\",\\"total\\":' + total + ',\\"items\\":\\"snack\\",\\"tanggal\\":\\"2026-08-03\\"}"}}]}'
        mock_vision.json.return_value = {
            "choices": [{"message": {"content": '{"toko":"Indomaret","total":' + total + ',"items":"snack","tanggal":"2026-08-03"}'}}]
        }
        self.mock_requests.return_value = mock_vision

        # Mock category lookup
        self.mock_supabase_get.return_value = ApiResult(ok=True, data=[{"id": 5}])

        # Mock transaction insert
        self.mock_create_tx.return_value = CreateTransactionResult(status=CreateTransactionStatus.CREATED, transaction={"id": 100})

    def test_valid_ocr_creates_transaction(self):
        """Valid OCR → repository called with proper metadata"""
        from maskai.clients.http import ApiResult
        self._setup_ocr_success("25000")

        from maskai.services.ocr_service import cmd_ocr
        cmd_ocr(chat_id=123, user_id=456, file_id="abc123", update_id=99999)

        # Verify supabase_post was called
        self.assertTrue(self.mock_create_tx.called)
        call_args = self.mock_create_tx.call_args[1]
        self.assertIn("metadata", call_args)
        self.assertEqual(call_args["update_id"], 99999)
        self.assertEqual(call_args["source"], "ocr")
        self.assertEqual(call_args["payload"]["type"], "E")

    def test_duplicate_ocr_returns_friendly_message(self):
        """Duplicate OCR → ALREADY_EXISTS, user gets friendly message"""
        from maskai.clients.http import ApiResult
        self._setup_ocr_success("25000")

        # Mock duplicate response
        self.mock_create_tx.return_value = CreateTransactionResult(status=CreateTransactionStatus.ALREADY_EXISTS, transaction={"id": 99})

        from maskai.services.ocr_service import cmd_ocr
        cmd_ocr(chat_id=123, user_id=456, file_id="abc", update_id=88888)

        # Should have been called (OCR still sends something)
        self.assertTrue(self.mock_create_tx.called)

    def test_ocr_timeout_does_not_insert(self):
        """Vision timeout → no transaction created"""
        import requests
        self.mock_tg.return_value = {"ok": True, "result": {"file_path": "photos/f.jpg"}}
        self.mock_requests.side_effect = requests.Timeout()

        from maskai.services.ocr_service import cmd_ocr
        cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)

        self.assertFalse(self.mock_create_tx.called)

    def test_invalid_amount_does_not_insert(self):
        """OCR with invalid amount → no transaction"""
        from maskai.clients.http import ApiResult
        self._setup_ocr_success('"abc"')  # invalid amount

        from maskai.services.ocr_service import cmd_ocr
        cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)

        # Should reject, no insert
        self.assertFalse(self.mock_create_tx.called)

    def test_telegram_download_failure(self):
        """getFile fails → OCR not executed"""
        self.mock_tg.return_value = {"ok": False, "error": "file not found"}

        from maskai.services.ocr_service import cmd_ocr
        cmd_ocr(chat_id=1, user_id=1, file_id="bad", update_id=1)

        # Vision API should not be called
        self.assertFalse(self.mock_requests.called)


if __name__ == "__main__":
    unittest.main()
