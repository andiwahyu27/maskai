"""CR-012: OCR production-path tests — error boundaries"""
import unittest
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOCRErrorBoundaries(unittest.TestCase):
    """Tests OCR error handling — all HTTP mocked"""

    def _mock_download_ok(self):
        import io
        mr = MagicMock()
        mr.status_code = 200
        mr.content = b'fake-jpeg-bytes'
        mr.headers = {'Content-Type': 'image/jpeg'}
        return mr
    """Tests OCR error handling — all HTTP mocked, no real network"""

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_timeout_no_insert(self, mock_tg, mock_send):
        """Vision timeout → repository not called"""
        import requests
        mock_tg.return_value = {"ok": True, "result": {"file_path": "f.jpg"}}

        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok()
        with patch('maskai.services.ocr_service.requests.post') as mv:
            mv.side_effect = requests.Timeout()
            from maskai.services.ocr_service import cmd_ocr
            with patch('maskai.services.ocr_service.supabase_post') as mp:
                cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertFalse(mp.called)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_connection_error_no_insert(self, mock_tg, mock_send):
        """Vision connection error → no insert"""
        import requests
        mock_tg.return_value = {"ok": True, "result": {"file_path": "f.jpg"}}
        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok()
        with patch('maskai.services.ocr_service.requests.post') as mv:
            mv.side_effect = requests.ConnectionError()
            from maskai.services.ocr_service import cmd_ocr
            with patch('maskai.services.ocr_service.supabase_post') as mp:
                cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertFalse(mp.called)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_request_exception_no_insert(self, mock_tg, mock_send):
        """Generic request exception → no insert"""
        import requests
        mock_tg.return_value = {"ok": True, "result": {"file_path": "f.jpg"}}
        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok()
        with patch('maskai.services.ocr_service.requests.post') as mv:
            mv.side_effect = requests.RequestException("fail")
            from maskai.services.ocr_service import cmd_ocr
            with patch('maskai.services.ocr_service.supabase_post') as mp:
                cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertFalse(mp.called)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_invalid_json_no_insert(self, mock_tg, mock_send):
        """Vision returns malformed JSON → graceful fail"""
        mock_tg.return_value = {"ok": True, "result": {"file_path": "f.jpg"}}
        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok()
        with patch('maskai.services.ocr_service.requests.post') as mv:
            mr = MagicMock()
            mr.status_code = 200
            mr.json.side_effect = ValueError("bad json")
            mr.text = "not json"
            mv.return_value = mr
            from maskai.services.ocr_service import cmd_ocr
            with patch('maskai.services.ocr_service.supabase_post') as mp:
                cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertFalse(mp.called)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_payload_not_dict_no_insert(self, mock_tg, mock_send):
        """Vision returns list/None/string instead of dict → graceful fail"""
        mock_tg.return_value = {"ok": True, "result": {"file_path": "f.jpg"}}
        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok()
        with patch('maskai.services.ocr_service.requests.post') as mv:
            mr = MagicMock()
            mr.status_code = 200
            mr.json.return_value = {"choices": [{"message": {"content": "[]"}}]}
            mr.text = '{"ok":true}'
            mv.return_value = mr
            from maskai.services.ocr_service import cmd_ocr
            with patch('maskai.services.ocr_service.supabase_post') as mp:
                cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertFalse(mp.called)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_invalid_amount_no_insert(self, mock_tg, mock_send):
        """OCR with non-numeric total → no insert"""
        mock_tg.return_value = {"ok": True, "result": {"file_path": "f.jpg"}}
        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok()
        with patch('maskai.services.ocr_service.requests.post') as mv:
            mr = MagicMock()
            mr.status_code = 200
            mr.json.return_value = {"choices": [{"message": {"content": '{"total":"abc"}'}}]}
            mr.text = '{"ok":true}'
            mv.return_value = mr
            from maskai.services.ocr_service import cmd_ocr
            with patch('maskai.services.ocr_service.supabase_post') as mp:
                cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertFalse(mp.called)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_telegram_getfile_fails_no_vision(self, mock_tg, mock_send):
        """Telegram download fails → vision API not called"""
        mock_tg.return_value = {"ok": False, "description": "file not found"}
        with patch('maskai.services.ocr_service.requests.post') as mv:
            from maskai.services.ocr_service import cmd_ocr
            cmd_ocr(chat_id=1, user_id=1, file_id="bad", update_id=1)
            self.assertFalse(mv.called)


if __name__ == "__main__":
    unittest.main()
