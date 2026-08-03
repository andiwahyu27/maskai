"""CR-010 Dahono client tests"""
import unittest
import logging
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDahonoClient(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("maskai.dahono")

    @patch('maskai.clients.dahono.requests.post')
    def test_success_returns_content(self, mock_post):
        """HTTP 200 + valid JSON → returns string"""
        from maskai.clients.dahono import claude
        mock_r = MagicMock()
        mock_r.status_code = 200
        mock_r.json.return_value = {"choices": [{"message": {"content": "Hello"}}]}
        mock_post.return_value = mock_r

        result = claude([{"role": "user", "content": "hi"}])
        self.assertEqual(result, "Hello")

    @patch('maskai.clients.dahono.requests.post')
    def test_timeout_returns_none(self, mock_post):
        """Timeout → None"""
        from maskai.clients.dahono import claude
        import requests
        mock_post.side_effect = requests.Timeout()

        with self.assertLogs(self.logger, level='ERROR') as cm:
            result = claude([{"role": "user", "content": "hi"}])
        self.assertIsNone(result)
        self.assertIn("timeout", "\n".join(cm.output).lower())

    @patch('maskai.clients.dahono.requests.post')
    def test_connection_error_returns_none(self, mock_post):
        """ConnectionError → None"""
        from maskai.clients.dahono import claude
        import requests
        mock_post.side_effect = requests.ConnectionError()

        result = claude([{"role": "user", "content": "hi"}])
        self.assertIsNone(result)

    @patch('maskai.clients.dahono.requests.post')
    def test_request_exception_does_not_leak_key(self, mock_post):
        """RequestException with key in message → key NOT in log, returns None"""
        from maskai.clients.dahono import claude
        from maskai.config import config
        import requests

        exc = requests.RequestException(
            f"Failed to connect to {config.DAHONO_URL}/chat with key={config.DAHONO_KEY}"
        )
        mock_post.side_effect = exc

        with self.assertLogs(self.logger, level='ERROR') as cm:
            result = claude([{"role": "user", "content": "hi"}])
        self.assertIsNone(result)
        output = "\n".join(cm.output)
        self.assertNotIn(config.DAHONO_KEY, output)

    @patch('maskai.clients.dahono.requests.post')
    def test_http_500_returns_none(self, mock_post):
        """HTTP 500 → None, no body in log"""
        from maskai.clients.dahono import claude
        mock_r = MagicMock()
        mock_r.status_code = 500
        mock_r.text = "Internal Server Error: sensitive data"
        mock_post.return_value = mock_r

        with self.assertLogs(self.logger, level='WARNING') as cm:
            result = claude([{"role": "user", "content": "hi"}])
        self.assertIsNone(result)
        output = "\n".join(cm.output)
        self.assertNotIn("sensitive data", output)

    @patch('maskai.clients.dahono.requests.post')
    def test_invalid_json_returns_none(self, mock_post):
        """Malformed JSON → None"""
        from maskai.clients.dahono import claude
        mock_r = MagicMock()
        mock_r.status_code = 200
        mock_r.json.side_effect = ValueError("bad json")
        mock_post.return_value = mock_r

        result = claude([{"role": "user", "content": "hi"}])
        self.assertIsNone(result)

    @patch('maskai.clients.dahono.requests.post')
    def test_malformed_schema_returns_none(self, mock_post):
        """Empty JSON object → None"""
        from maskai.clients.dahono import claude
        mock_r = MagicMock()
        mock_r.status_code = 200
        mock_r.json.return_value = {}
        mock_post.return_value = mock_r

        result = claude([{"role": "user", "content": "hi"}])
        self.assertIsNone(result)

    @patch('maskai.clients.dahono.requests.post')
    def test_empty_content_returns_none(self, mock_post):
        """Empty content string → None"""
        from maskai.clients.dahono import claude
        mock_r = MagicMock()
        mock_r.status_code = 200
        mock_r.json.return_value = {"choices": [{"message": {"content": ""}}]}
        mock_post.return_value = mock_r

        result = claude([{"role": "user", "content": "hi"}])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
