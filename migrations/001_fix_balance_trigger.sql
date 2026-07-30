-- MASKAI Balance Trigger Migration v2
-- Fixes CR-004 + ambiguous column fix

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
        delta := CASE WHEN OLD.type = 'I' THEN -OLD.amount ELSE OLD.amount END;
        UPDATE maskai_balance SET balance = balance + delta WHERE user_id = OLD.user_id;
        delta := CASE WHEN NEW.type = 'I' THEN NEW.amount ELSE -NEW.amount END;
        UPDATE maskai_balance SET balance = balance + delta WHERE user_id = NEW.user_id;
    
    ELSIF TG_OP = 'DELETE' THEN
        delta := CASE WHEN OLD.type = 'I' THEN -OLD.amount ELSE OLD.amount END;
        UPDATE maskai_balance SET balance = balance + delta WHERE user_id = OLD.user_id;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_balance ON maskai_transactions;
CREATE TRIGGER trg_update_balance
    AFTER INSERT OR UPDATE OR DELETE ON maskai_transactions
    FOR EACH ROW EXECUTE FUNCTION maskai_update_balance();

CREATE OR REPLACE FUNCTION maskai_reset_user(p_user_id BIGINT)
RETURNS VOID AS $$
BEGIN
    DELETE FROM maskai_transactions WHERE user_id = p_user_id;
    DELETE FROM maskai_debts WHERE user_id = p_user_id;
    DELETE FROM maskai_keranjang WHERE user_id = p_user_id;
    INSERT INTO maskai_balance (user_id, balance) VALUES (p_user_id, 0)
    ON CONFLICT (user_id) DO UPDATE SET balance = 0;
END;
$$ LANGUAGE plpgsql;
