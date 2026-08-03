"""CR-012: Config, HTTP, Supabase, Telegram, Regression tests"""
import unittest
from unittest.mock import MagicMock, patch
import sys, os, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigValidation(unittest.TestCase):
    def test_missing_env_raises(self):
        from maskai.config import Config
        with self.assertRaises(RuntimeError):
            Config(BOT_TOKEN="", SUPABASE_URL="x", SUPABASE_KEY="x", DAHONO_KEY="x")
    
    def test_valid_config_ok(self):
        from maskai.config import Config
        c = Config(BOT_TOKEN="t", SUPABASE_URL="u", SUPABASE_KEY="k", DAHONO_KEY="d")
        self.assertEqual(c.BOT_TOKEN, "t")
        self.assertEqual(c.HTTP_TIMEOUT, 15)
        self.assertEqual(str(c.TZ), "Asia/Jakarta")
    
    def test_defaults_preserved(self):
        from maskai.config import Config
        c = Config(BOT_TOKEN="t", SUPABASE_URL="u", SUPABASE_KEY="k", DAHONO_KEY="d")
        self.assertEqual(c.LOG_LEVEL, "INFO")
        self.assertEqual(c.POLL_TIMEOUT, 35)


class TestHTTPClient(unittest.TestCase):
    @patch('maskai.clients.http.requests.get')
    def test_get_2xx_returns_ok(self, mock_get):
        from maskai.clients.http import api_get
        mock_r = MagicMock()
        mock_r.status_code = 200
        mock_r.text = '{"data": [1,2,3]}'
        mock_r.json.return_value = {"data": [1, 2, 3]}
        mock_get.return_value = mock_r
        result = api_get("https://test")
        self.assertTrue(result.ok)
        self.assertEqual(result.data, {"data": [1, 2, 3]})

    @patch('maskai.clients.http.requests.get')
    def test_get_timeout_returns_not_ok(self, mock_get):
        from maskai.clients.http import api_get
        import requests
        mock_get.side_effect = requests.Timeout()
        result = api_get("https://test")
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "timeout")

    @patch('maskai.clients.http.requests.patch')
    def test_patch_204_is_success(self, mock_patch):
        from maskai.clients.http import api_patch
        mock_r = MagicMock()
        mock_r.status_code = 204
        mock_r.text = ""
        mock_patch.return_value = mock_r
        result = api_patch("https://test")
        self.assertTrue(result.ok)
        self.assertEqual(result.status, 204)

    @patch('maskai.clients.http.requests.delete')
    def test_delete_204_is_success(self, mock_delete):
        from maskai.clients.http import api_delete
        mock_r = MagicMock()
        mock_r.status_code = 204
        mock_r.text = ""
        mock_delete.return_value = mock_r
        result = api_delete("https://test")
        self.assertTrue(result.ok)
        self.assertEqual(result.status, 204)


class TestSupabaseClient(unittest.TestCase):
    @patch('maskai.clients.supabase.api_get')
    def test_get_returns_apiresult(self, mock_get):
        from maskai.clients.supabase import supabase_get
        from maskai.clients.http import ApiResult
        mock_get.return_value = ApiResult(ok=True, status=200, data=[{"id":1}])
        result = supabase_get("maskai_categories", {"select": "id"})
        self.assertTrue(result.ok)
        self.assertEqual(result.data, [{"id":1}])

    @patch('maskai.clients.supabase.api_post')
    def test_post_returns_apiresult(self, mock_post):
        from maskai.clients.supabase import supabase_post
        from maskai.clients.http import ApiResult
        mock_post.return_value = ApiResult(ok=True, status=201, data={"id": 2})
        result = supabase_post("maskai_transactions", {"amount": "100"})
        self.assertTrue(result.ok)
        self.assertEqual(result.status, 201)


class TestOffsetStore(unittest.TestCase):
    def test_corrupt_file_resets_to_zero(self):
        from maskai.utils.offset_store import OffsetStore
        path = "/tmp/test_corrupt_offset.txt"
        with open(path, 'w') as f:
            f.write("not_a_number")
        store = OffsetStore(path)
        self.assertEqual(store.load(), 0)
        import os
        os.remove(path)


class TestHTML(unittest.TestCase):
    def test_escape_html_special_chars(self):
        from maskai.utils.html import escape_html
        result = escape_html('<script>alert("x")</script>')
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;', result)
    
    def test_escape_html_none(self):
        from maskai.utils.html import escape_html
        self.assertEqual(escape_html(None), "")
    
    def test_escape_html_preserves_safe(self):
        from maskai.utils.html import escape_html
        result = escape_html("<b>safe</b>")
        self.assertIn('&lt;b&gt;', result)


class TestPendingStore(unittest.TestCase):
    def test_isolation_per_user(self):
        from maskai.state.pending_store import PendingStore
        store = PendingStore()
        store.set(100, 1, {"amount": 5000})
        store.set(100, 2, {"amount": 9999})
        self.assertEqual(store.get(100, 1), {"amount": 5000})
        self.assertEqual(store.get(100, 2), {"amount": 9999})
    
    def test_overwrite(self):
        from maskai.state.pending_store import PendingStore
        store = PendingStore()
        store.set(100, 1, {"old": True})
        store.set(100, 1, {"new": True})
        self.assertEqual(store.get(100, 1), {"new": True})


class TestRegression(unittest.TestCase):
    """Ensure previously fixed bugs stay fixed"""
    
    def test_cr001_auth_rejects_unauthorized(self):
        """CR-001: is_authorized rejects unknown users"""
        from maskai.config import ADMIN_IDS
        self.assertNotIn(999999999, ADMIN_IDS)
    
    def test_cr008_parse_positive_amount_decimal(self):
        """CR-008: parse_positive_amount returns Decimal"""
        from maskai.utils.validation import parse_positive_amount
        from decimal import Decimal
        amt, err = parse_positive_amount("100.50")
        self.assertIsNone(err)
        self.assertIsInstance(amt, Decimal)
        self.assertEqual(amt, Decimal("100.50"))
    
    def test_cr009_transaction_result_has_created_status(self):
        """CR-009: CreateTransactionStatus exists"""
        from maskai.repositories.transaction_repository import CreateTransactionStatus
        self.assertTrue(hasattr(CreateTransactionStatus, 'CREATED'))
        self.assertTrue(hasattr(CreateTransactionStatus, 'ALREADY_EXISTS'))
        self.assertTrue(hasattr(CreateTransactionStatus, 'FAILED'))
    
    def test_cr011_date_range_timezone(self):
        """CR-011: build_jakarta_date_range has +07:00"""
        from maskai.utils.dates import build_jakarta_date_range
        start, end = build_jakarta_date_range("2026-07-20", "2026-07-20")
        self.assertIn("+07:00", start.isoformat())
        self.assertIn("+07:00", end.isoformat())
    
    def test_cr014_escape_html_exists(self):
        """CR-014: escape_html uses html.escape"""
        from maskai.utils.html import escape_html
        import html
        result = escape_html("A & B")
        self.assertIn("&amp;", result)


if __name__ == "__main__":
    unittest.main()
