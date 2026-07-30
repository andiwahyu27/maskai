-- MASKAI Balance Trigger Migration
-- Fixes CR-004: trigger handles INSERT, UPDATE, DELETE
-- Safe to run multiple times (uses CREATE OR REPLACE)

BEGIN;

-- 1. Replace old trigger function
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
        -- Apply NEW
        delta := CASE WHEN NEW.type = 'I' THEN NEW.amount ELSE -NEW.amount END;
        UPDATE maskai_balance SET balance = balance + delta WHERE user_id = NEW.user_id;
    
    ELSIF TG_OP = 'DELETE' THEN
        -- Reverse OLD
        delta := CASE WHEN OLD.type = 'I' THEN -OLD.amount ELSE OLD.amount END;
        UPDATE maskai_balance SET balance = balance + delta WHERE user_id = OLD.user_id;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 2. Recreate trigger
DROP TRIGGER IF EXISTS trg_update_balance ON maskai_transactions;
CREATE TRIGGER trg_update_balance
    AFTER INSERT OR UPDATE OR DELETE ON maskai_transactions
    FOR EACH ROW EXECUTE FUNCTION maskai_update_balance();

-- 3. Reconciliation query — recalculate all balances
-- Run this manually after migration to fix existing data:
-- 
-- SELECT user_id, 
--   COALESCE(SUM(CASE WHEN type='I' THEN amount ELSE -amount END), 0) as recomputed_balance 
-- FROM maskai_transactions 
-- GROUP BY user_id;
--
-- UPDATE maskai_balance b 
-- SET balance = r.recomputed_balance
-- FROM (
--   SELECT user_id, 
--     COALESCE(SUM(CASE WHEN type='I' THEN amount ELSE -amount END), 0) as recomputed_balance 
--   FROM maskai_transactions 
--   GROUP BY user_id
-- ) r 
-- WHERE b.user_id = r.user_id;

-- 4. Atomic reset function
CREATE OR REPLACE FUNCTION maskai_reset_user(user_id BIGINT)
RETURNS VOID AS $$
BEGIN
    DELETE FROM maskai_transactions WHERE user_id = $1;
    DELETE FROM maskai_debts WHERE user_id = $1;
    DELETE FROM maskai_keranjang WHERE user_id = $1;
    -- Recompute balance after triggers fired
    INSERT INTO maskai_balance (user_id, balance) VALUES ($1, 0)
    ON CONFLICT (user_id) DO UPDATE SET balance = 0;
END;
$$ LANGUAGE plpgsql;

COMMIT;
