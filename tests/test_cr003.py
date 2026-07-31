"""CR-003 integration tests"""
import unittest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maskai.clients.supabase import supabase_get
from maskai.state.pending_store import PendingStore
from maskai.utils.offset_store import OffsetStore
from maskai.utils.validation import parse_positive_amount


class TestSupabaseClient(unittest.TestCase):
    def test_supabase_get_returns_apiresult(self):
        """supabase_get should return ApiResult with .ok attribute"""
        from maskai.clients.http import ApiResult
        result = supabase_get("maskai_categories", {"select": "id", "limit": "1"})
        self.assertTrue(hasattr(result, 'ok'))
        self.assertTrue(hasattr(result, 'data'))
        self.assertTrue(hasattr(result, 'status'))


class TestPendingStore(unittest.TestCase):
    def test_isolated_per_user(self):
        store = PendingStore()
        store.set(100, 1, {"amount": 5000})
        store.set(100, 2, {"amount": 10000})
        self.assertEqual(store.get(100, 1), {"amount": 5000})
        self.assertEqual(store.get(100, 2), {"amount": 10000})
    
    def test_pop_removes(self):
        store = PendingStore()
        store.set(100, 1, {"amount": 5000})
        val = store.pop(100, 1)
        self.assertEqual(val, {"amount": 5000})
        self.assertIsNone(store.get(100, 1))
    
    def test_different_chats(self):
        store = PendingStore()
        store.set(100, 1, {"x": 1})
        store.set(200, 1, {"x": 2})
        self.assertEqual(store.get(100, 1), {"x": 1})
        self.assertEqual(store.get(200, 1), {"x": 2})


class TestOffsetStore(unittest.TestCase):
    def test_load_empty(self):
        store = OffsetStore("/tmp/test_offset_nonexistent.txt")
        self.assertEqual(store.load(), 0)
    
    def test_save_and_load(self):
        path = "/tmp/test_offset_cr003.txt"
        store = OffsetStore(path)
        store.save(12345)
        self.assertEqual(store.load(), 12345)
        os.remove(path) if os.path.exists(path) else None


class TestValidation(unittest.TestCase):
    def test_positive_amount(self):
        amt, err = parse_positive_amount("10000.50")
        self.assertIsNone(err)
        self.assertEqual(str(amt), "10000.50")
    
    def test_zero_rejected(self):
        amt, err = parse_positive_amount("0")
        self.assertIsNotNone(err)
    
    def test_negative_rejected(self):
        amt, err = parse_positive_amount("-100")
        self.assertIsNotNone(err)


if __name__ == "__main__":
    unittest.main()
