-- MASKAI Balance Reconciliation & UPSERT fix
-- Fixes: UPDATE moving transaction to user without balance row

-- 1. UPSERT in trigger — ensure balance row exists for INSERT
CREATE OR REPLACE FUNCTION maskai_update_balance()
RETURNS TRIGGER AS $$
DECLARE
    delta NUMERIC;
BEGIN
    IF TG_OP = 'INSERT' THEN
        delta := CASE WHEN NEW.type = 'I' THEN NEW.amount ELSE -NEW.amount END;
        INSERT INTO maskai_balance (user_id, balance)
        VALUES (NEW.user_id, delta)
        ON CONFLICT (user_id) DO UPDATE SET balance = maskai_balance.balance + delta;
    
    ELSIF TG_OP = 'UPDATE' THEN
        -- Rollback OLD
        delta := CASE WHEN OLD.type = 'I' THEN -OLD.amount ELSE OLD.amount END;
        UPDATE maskai_balance SET balance = balance + delta WHERE user_id = OLD.user_id;
        -- Apply NEW (use UPSERT in case user has no balance row)
        delta := CASE WHEN NEW.type = 'I' THEN NEW.amount ELSE -NEW.amount END;
        INSERT INTO maskai_balance (user_id, balance)
        VALUES (NEW.user_id, delta)
        ON CONFLICT (user_id) DO UPDATE SET balance = maskai_balance.balance + delta;
    
    ELSIF TG_OP = 'DELETE' THEN
        delta := CASE WHEN OLD.type = 'I' THEN -OLD.amount ELSE OLD.amount END;
        UPDATE maskai_balance SET balance = balance + delta WHERE user_id = OLD.user_id;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 2. Reconciliation — recalculate ALL balances from scratch
-- Run this if balance numbers look wrong:
/*
SELECT 
    b.user_id,
    b.balance AS current_balance,
    COALESCE(t.computed, 0) AS recomputed_balance
FROM maskai_balance b
LEFT JOIN (
    SELECT user_id, 
        COALESCE(SUM(CASE WHEN type='I' THEN amount ELSE -amount END), 0) AS computed
    FROM maskai_transactions
    GROUP BY user_id
) t ON b.user_id = t.user_id
WHERE b.balance != COALESCE(t.computed, 0);

-- Uncomment to fix:
-- UPDATE maskai_balance b
-- SET balance = COALESCE(t.computed, 0)
-- FROM (
--     SELECT user_id, 
--         COALESCE(SUM(CASE WHEN type='I' THEN amount ELSE -amount END), 0) AS computed
--     FROM maskai_transactions
--     GROUP BY user_id
-- ) t
-- WHERE b.user_id = t.user_id;
*/
