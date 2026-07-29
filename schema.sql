-- MASKAI Personal Finance Tracker — Supabase Schema
-- Execute this in Supabase SQL Editor

-- 1. CATEGORIES
CREATE TABLE maskai_categories (
    id          BIGSERIAL       PRIMARY KEY,
    user_id     BIGINT          NOT NULL,
    name        VARCHAR(100)    NOT NULL,
    type        CHAR(1)         NOT NULL CHECK (type IN ('I', 'E')),
    icon        VARCHAR(32)     DEFAULT '📦',
    parent_id   BIGINT          REFERENCES maskai_categories(id) ON DELETE SET NULL,
    is_archived BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_cat_user_name UNIQUE (user_id, name)
);
CREATE INDEX idx_mc_user ON maskai_categories(user_id);
CREATE INDEX idx_mc_type ON maskai_categories(type);

-- 2. TRANSACTIONS
CREATE TABLE maskai_transactions (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    type            CHAR(1)         NOT NULL CHECK (type IN ('I', 'E')),
    amount          NUMERIC(12,2)   NOT NULL CHECK (amount > 0),
    currency        VARCHAR(3)      NOT NULL DEFAULT 'IDR',
    category_id     BIGINT          NOT NULL REFERENCES maskai_categories(id),
    description     TEXT,
    transaction_dt  TIMESTAMPTZ     NOT NULL,
    is_reconciled   BOOLEAN         NOT NULL DEFAULT FALSE,
    metadata        JSONB           DEFAULT '{}',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_mt_user   ON maskai_transactions(user_id);
CREATE INDEX idx_mt_type   ON maskai_transactions(type);
CREATE INDEX idx_mt_cat    ON maskai_transactions(category_id);
CREATE INDEX idx_mt_date   ON maskai_transactions(transaction_dt);
CREATE INDEX idx_mt_udate  ON maskai_transactions(user_id, transaction_dt DESC);

-- 3. DEBTS & RECEIVABLES
CREATE TABLE maskai_debts (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    counterparty    VARCHAR(255)    NOT NULL,
    direction       CHAR(1)         NOT NULL CHECK (direction IN ('O', 'T')),
    amount          NUMERIC(12,2)   NOT NULL CHECK (amount > 0),
    currency        VARCHAR(3)      NOT NULL DEFAULT 'IDR',
    description     TEXT,
    due_date        DATE,
    status          VARCHAR(20)     NOT NULL DEFAULT 'open' CHECK (status IN ('open','partially_paid','closed','written_off')),
    amount_paid     NUMERIC(12,2)   NOT NULL DEFAULT 0 CHECK (amount_paid >= 0),
    settled_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_paid_lte_amount CHECK (amount_paid <= amount)
);
CREATE INDEX idx_md_user   ON maskai_debts(user_id);
CREATE INDEX idx_md_status ON maskai_debts(status);
CREATE INDEX idx_md_dir    ON maskai_debts(direction);

-- 4. BALANCE (latest snapshot per user)
CREATE TABLE maskai_balance (
    user_id         BIGINT          NOT NULL PRIMARY KEY,
    balance         NUMERIC(14,2)   NOT NULL DEFAULT 0,
    currency        VARCHAR(3)      NOT NULL DEFAULT 'IDR',
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Auto-update balance trigger
CREATE OR REPLACE FUNCTION maskai_update_balance()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO maskai_balance (user_id, balance, currency, updated_at)
    VALUES (
        NEW.user_id,
        CASE WHEN NEW.type = 'I' THEN NEW.amount ELSE -NEW.amount END,
        NEW.currency,
        NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        balance = maskai_balance.balance + CASE WHEN NEW.type = 'I' THEN NEW.amount ELSE -NEW.amount END,
        currency = CASE WHEN maskai_balance.currency != NEW.currency THEN 'MULTI' ELSE maskai_balance.currency END,
        updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_maskai_balance
    AFTER INSERT ON maskai_transactions
    FOR EACH ROW EXECUTE FUNCTION maskai_update_balance();

-- 5. Default categories
INSERT INTO maskai_categories (user_id, name, type, icon) VALUES
    (0, 'Makanan & Minuman', 'E', '🍽️'),
    (0, 'Transportasi', 'E', '🚗'),
    (0, 'Belanja', 'E', '🛒'),
    (0, 'Tagihan', 'E', '📄'),
    (0, 'Hiburan', 'E', '🎬'),
    (0, 'Kesehatan', 'E', '💊'),
    (0, 'Pendidikan', 'E', '📚'),
    (0, 'Lainnya (Pengeluaran)', 'E', '📦'),
    (0, 'Gaji', 'I', '💰'),
    (0, 'Freelance', 'I', '💼'),
    (0, 'Investasi', 'I', '📈'),
    (0, 'Lainnya (Pemasukan)', 'I', '📦');
