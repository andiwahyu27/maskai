"""V2-DB-001: Database constraint tests"""
import unittest
from unittest.mock import MagicMock, patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDBConstraints(unittest.TestCase):
    @patch('maskai.repositories.transaction_repository.supabase_post')
    def test_typed_update_id_in_payload(self, mock_post):
        """Repository includes typed telegram_update_id in payload"""
        from maskai.clients.http import ApiResult
        from maskai.repositories.transaction_repository import create_transaction

        mock_post.return_value = ApiResult(ok=True, data={"id": 1})

        create_transaction(
            user_id=1, update_id=99999,
            payload={"type": "E", "amount": "10000"},
            source="test",
        )

        call_payload = mock_post.call_args[0][1]
        # Typed column must be present for unique index
        self.assertIn("telegram_update_id", call_payload)
        self.assertEqual(call_payload["telegram_update_id"], 99999)
        # Metadata also preserved
        self.assertIn("metadata", call_payload)
        self.assertEqual(call_payload["metadata"]["telegram_update_id"], "99999")

    @patch('maskai.repositories.transaction_repository.supabase_post')
    def test_duplicate_still_23505(self, mock_post):
        """23505 duplicate violation still returns ALREADY_EXISTS"""
        from maskai.clients.http import ApiResult
        from maskai.repositories.transaction_repository import create_transaction, CreateTransactionStatus

        mock_post.return_value = ApiResult(
            ok=False, status=409,
            data={"code": "23505", "message": "duplicate key value violates unique constraint uq_maskai_transactions_user_update"},
        )

        result = create_transaction(
            user_id=1, update_id=88888,
            payload={"type": "E", "amount": "5000"},
            source="test",
        )
        self.assertEqual(result.status, CreateTransactionStatus.ALREADY_EXISTS)


class TestFKRestrict(unittest.TestCase):
    def test_fk_restrict_migration_exists(self):
        """Migration 003 exists with ON DELETE RESTRICT"""
        with open('migrations/003_add_explicit_fk_restrict.sql') as f:
            content = f.read()
        self.assertIn("ON DELETE RESTRICT", content)
        self.assertIn("maskai_transactions_category_id_fkey", content)


class TestTypedColumn(unittest.TestCase):
    def test_typed_column_migration_exists(self):
        """Migration 004 exists for typed telegram_update_id"""
        with open('migrations/004_add_typed_update_id.sql') as f:
            content = f.read()
        self.assertIn("ADD COLUMN IF NOT EXISTS telegram_update_id", content)
        self.assertIn("USING btree (user_id, telegram_update_id)", content)


if __name__ == "__main__":
    unittest.main()
