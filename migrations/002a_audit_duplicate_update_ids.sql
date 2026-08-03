-- CR-009: Audit duplicate telegram_update_id BEFORE creating unique index
-- Run this FIRST. If result != 0 rows, cleanup duplicates before proceeding to 002b.

SELECT
    user_id,
    metadata->>'telegram_update_id' AS update_id,
    COUNT(*) AS duplicate_count
FROM maskai_transactions
WHERE metadata->>'telegram_update_id' IS NOT NULL
GROUP BY user_id, metadata->>'telegram_update_id'
HAVING COUNT(*) > 1;

-- Expected: 0 rows
-- If rows returned: manually resolve duplicates, then run 002b
