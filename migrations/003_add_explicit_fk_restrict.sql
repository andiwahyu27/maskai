-- V2-DB-001: Explicit ON DELETE RESTRICT for transaction → category FK
-- Safe to run multiple times (uses IF EXISTS / IF NOT EXISTS)

BEGIN;

ALTER TABLE maskai_transactions
DROP CONSTRAINT IF EXISTS maskai_transactions_category_id_fkey;

ALTER TABLE maskai_transactions
ADD CONSTRAINT maskai_transactions_category_id_fkey
FOREIGN KEY (category_id)
REFERENCES maskai_categories(id)
ON DELETE RESTRICT;

COMMIT;

-- Verify: SELECT conname, confdeltype FROM pg_constraint
-- WHERE conrelid = 'maskai_transactions'::regclass AND conname = 'maskai_transactions_category_id_fkey';
-- Expected: confdeltype = 'r'
