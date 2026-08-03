"""V2-SEC-001: Token boundary test — BOT_TOKEN never leaves MASKAI"""
import unittest
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSecureOCRTransfer(unittest.TestCase):
    def _mock_telegram_getfile(self):
        return {"ok": True, "result": {"file_path": "photos/test.jpg"}}

    def _mock_download_ok(self, content_type="image/jpeg"):
        mr = MagicMock()
        mr.status_code = 200
        mr.content = b'\xff\xd8\xff\xe0\x00\x10JFIF'  # JPEG magic bytes
        mr.headers = {"Content-Type": content_type}
        return mr

    def _mock_vision_ok(self):
        mr = MagicMock()
        mr.status_code = 200
        mr.json.return_value = {
            "choices": [{"message": {"content": '{"toko":"Test","total":25000,"items":"item","tanggal":"2026-08-03"}'}}]
        }
        mr.text = '{"ok":true}'
        return mr

    @patch('maskai.services.ocr_service.supabase_post')
    @patch('maskai.services.ocr_service.supabase_get')
    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_bot_token_not_in_dahono_payload(self, mock_tg, mock_send, mock_get, mock_post):
        """BOT_TOKEN must NEVER appear in Dahono Vision payload"""
        from maskai.clients.http import ApiResult
        from maskai.config import config

        mock_tg.return_value = self._mock_telegram_getfile()
        mock_get.return_value = ApiResult(ok=True, data=[])
        mock_post.return_value = ApiResult(ok=True, data={"id": 1})

        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok()
            with patch('maskai.services.ocr_service.requests.post') as mp:
                mp.return_value = self._mock_vision_ok()

                from maskai.services.ocr_service import cmd_ocr
                cmd_ocr(chat_id=1, user_id=1, file_id="abc", update_id=99999)

                # Capture the Dahono payload
                self.assertTrue(mp.called)
                payload = mp.call_args[1]["json"]
                payload_str = str(payload)

                # BOT_TOKEN must not appear
                self.assertNotIn(config.BOT_TOKEN, payload_str)
                # Telegram file URL must not appear
                self.assertNotIn("api.telegram.org/file/bot", payload_str)
                # Must use base64 data URL
                image_url = payload["messages"][0]["content"][1]["image_url"]["url"]
                self.assertTrue(image_url.startswith("data:image/jpeg;base64,"))

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_png_success(self, mock_tg, mock_send):
        """PNG images are accepted"""
        from maskai.clients.http import ApiResult

        mock_tg.return_value = self._mock_telegram_getfile()

        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok("image/png")
            with patch('maskai.services.ocr_service.requests.post') as mp:
                mp.return_value = self._mock_vision_ok()
                with patch('maskai.services.ocr_service.supabase_post') as msp:
                    msp.return_value = ApiResult(ok=True, data={"id": 2})
                    with patch('maskai.services.ocr_service.supabase_get') as msg:
                        msg.return_value = ApiResult(ok=True, data=[])
                        from maskai.services.ocr_service import cmd_ocr
                        cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                # Should use PNG mime in data URL
                payload_str = str(mp.call_args[1]["json"])
                self.assertIn("data:image/png;base64,", payload_str)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_webp_success(self, mock_tg, mock_send):
        """WebP images are accepted"""
        from maskai.clients.http import ApiResult

        mock_tg.return_value = self._mock_telegram_getfile()

        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok("image/webp")
            with patch('maskai.services.ocr_service.requests.post') as mp:
                mp.return_value = self._mock_vision_ok()
                with patch('maskai.services.ocr_service.supabase_post') as msp:
                    msp.return_value = ApiResult(ok=True, data={"id": 3})
                    with patch('maskai.services.ocr_service.supabase_get') as msg:
                        msg.return_value = ApiResult(ok=True, data=[])
                        from maskai.services.ocr_service import cmd_ocr
                        cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertTrue(mp.called)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_unsupported_mime_rejected(self, mock_tg, mock_send):
        """PDF is rejected"""
        mock_tg.return_value = self._mock_telegram_getfile()
        with patch('maskai.services.ocr_service.requests.get') as mg:
            mg.return_value = self._mock_download_ok("application/pdf")
            with patch('maskai.services.ocr_service.requests.post') as mp:
                from maskai.services.ocr_service import cmd_ocr
                cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertFalse(mp.called)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_empty_file_rejected(self, mock_tg, mock_send):
        """Empty image body is rejected"""
        mock_tg.return_value = self._mock_telegram_getfile()
        with patch('maskai.services.ocr_service.requests.get') as mg:
            mr = MagicMock()
            mr.status_code = 200
            mr.content = b""
            mr.headers = {"Content-Type": "image/jpeg"}
            mg.return_value = mr
            with patch('maskai.services.ocr_service.requests.post') as mp:
                from maskai.services.ocr_service import cmd_ocr
                cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertFalse(mp.called)

    @patch('maskai.services.ocr_service.send')
    @patch('maskai.services.ocr_service.tg')
    def test_too_large_rejected(self, mock_tg, mock_send):
        """Image over OCR_MAX_IMAGE_BYTES is rejected"""
        from maskai.config import config
        mock_tg.return_value = self._mock_telegram_getfile()
        with patch('maskai.services.ocr_service.requests.get') as mg:
            mr = MagicMock()
            mr.status_code = 200
            mr.content = b'x' * (config.OCR_MAX_IMAGE_BYTES + 1)
            mr.headers = {"Content-Type": "image/jpeg"}
            mg.return_value = mr
            with patch('maskai.services.ocr_service.requests.post') as mp:
                from maskai.services.ocr_service import cmd_ocr
                cmd_ocr(chat_id=1, user_id=1, file_id="f", update_id=1)
                self.assertFalse(mp.called)


if __name__ == "__main__":
    unittest.main()
