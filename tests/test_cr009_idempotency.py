"""CR-009 Idempotency Tests"""
import unittest
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maskai.repositories.transaction_repository import (
    create_transaction, CreateTransactionStatus,
    CreateTransactionResult, is_unique_violation,
)


class MockApiResult:
    def __init__(self, ok=True, data=None, status=200, error=None):
        self.ok = ok
        self.data = data
        self.status = status
        self.error = error


class TestTransactionRepository(unittest.TestCase):
    @patch('maskai.repositories.transaction_repository.supabase_post')
    @patch('maskai.repositories.transaction_repository.supabase_get')
    def test_first_insert_returns_created(self, mock_get, mock_post):
        """First insert → CREATED"""
        mock_post.return_value = MockApiResult(ok=True, data={"id": 1, "amount": "10000"})
        result = create_transaction(
            user_id=1367356347,
            update_id=12345,
            payload={"type": "E", "amount": "10000", "description": "test"},
            source="test",
        )
        self.assertEqual(result.status, CreateTransactionStatus.CREATED)
        self.assertIsNotNone(result.transaction)

    @patch('maskai.repositories.transaction_repository.supabase_get')
    @patch('maskai.repositories.transaction_repository.supabase_post')
    def test_duplicate_sqlstate_23505_returns_already_exists(self, mock_post, mock_get):
        """SQLSTATE 23505 → ALREADY_EXISTS"""
        mock_post.return_value = MockApiResult(
            ok=False, status=409,
            data={"code": "23505", "message": "duplicate key value violates unique constraint uq_maskai_transactions_user_update"},
        )
        mock_get.return_value = MockApiResult(ok=True, data=[])
        result = create_transaction(
            user_id=1367356347,
            update_id=12345,
            payload={"type": "E", "amount": "10000"},
            source="test",
        )
        self.assertEqual(result.status, CreateTransactionStatus.ALREADY_EXISTS)

    @patch('maskai.repositories.transaction_repository.supabase_post')
    def test_other_error_returns_failed(self, mock_post):
        """Non-23505 error → FAILED"""
        mock_post.return_value = MockApiResult(ok=False, status=500, error="Internal error")
        result = create_transaction(
            user_id=1367356347,
            update_id=12345,
            payload={"type": "E", "amount": "10000"},
            source="test",
        )
        self.assertEqual(result.status, CreateTransactionStatus.FAILED)

    @patch('maskai.repositories.transaction_repository.supabase_post')
    def test_no_update_id_still_inserts(self, mock_post):
        """Insert without update_id works (legacy)"""
        mock_post.return_value = MockApiResult(ok=True, data={"id": 2})
        result = create_transaction(
            user_id=1367356347,
            update_id=None,
            payload={"type": "E", "amount": "10000"},
            source="test",
        )
        self.assertEqual(result.status, CreateTransactionStatus.CREATED)


class TestUniqueViolationDetection(unittest.TestCase):
    def test_sqlstate_23505_is_unique_violation(self):
        result = MockApiResult(data={"code": "23505"})
        self.assertTrue(is_unique_violation(result))

    def test_other_code_not_unique_violation(self):
        result = MockApiResult(data={"code": "22001"})
        self.assertFalse(is_unique_violation(result))

    def test_no_data_not_unique_violation(self):
        result = MockApiResult(data=None)
        self.assertFalse(is_unique_violation(result))


class TestUpdateRetry(unittest.TestCase):
    @patch('maskai.repositories.transaction_repository.supabase_get')
    @patch('maskai.repositories.transaction_repository.supabase_post')
    def test_same_update_id_processed_twice(self, mock_post, mock_get):
        """Same update processed twice → only one effective insert"""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MockApiResult(ok=True, data={"id": 1})
            else:
                return MockApiResult(
                    ok=False, status=409,
                    data={"code": "23505", "message": "duplicate"},
                )

        mock_post.side_effect = side_effect

        # First call
        r1 = create_transaction(user_id=1, update_id=99999, payload={"type": "E", "amount": "5000"}, source="test")
        self.assertEqual(r1.status, CreateTransactionStatus.CREATED)

        # Second call — same update_id
        r2 = create_transaction(user_id=1, update_id=99999, payload={"type": "E", "amount": "5000"}, source="test")
        self.assertEqual(r2.status, CreateTransactionStatus.ALREADY_EXISTS)

        # Repository was called twice
        self.assertEqual(call_count[0], 2)

    def test_metadata_merge_preserves_existing(self):
        """Metadata merge doesn't overwrite existing metadata"""
        from maskai.repositories.transaction_repository import create_transaction
        with patch('maskai.repositories.transaction_repository.supabase_post') as mock_post:
            mock_post.return_value = MockApiResult(ok=True, data={"id": 3})
            result = create_transaction(
                user_id=1, update_id=123,
                payload={"type": "E", "amount": "1000", "metadata": {"custom_field": "keep_me"}},
                source="test",
            )
            self.assertEqual(result.status, CreateTransactionStatus.CREATED)
            # Verify the payload sent to supabase_post had merged metadata
            call_payload = mock_post.call_args[0][1]
            self.assertIn("metadata", call_payload)
            self.assertEqual(call_payload["metadata"]["custom_field"], "keep_me")
            self.assertEqual(call_payload["metadata"]["source"], "test")
            self.assertEqual(call_payload["metadata"]["telegram_update_id"], "123")


if __name__ == "__main__":
    unittest.main()
