# Resolved Review Issues — Final Status

## P0 — Critical
| ID | Issue | Status |
|----|-------|--------|
| CR-001 | Authorization guard | ✅ Done |
| CR-002 | OCR user ownership | ✅ Done |
| CR-003 | Date range filter bug | ✅ Done |
| CR-004 | Balance trigger (INSERT/UPDATE/DELETE) | ✅ Done |

## P1 — High
| ID | Issue | Status |
|----|-------|--------|
| CR-005 | /tambahkat user_id + multi-word name | ✅ Done |
| CR-006 | Category ownership filter | ✅ Done |
| CR-007 | API result model | ✅ Done |
| CR-008 | Input validation (amount) | ✅ Done |
| CR-009 | Telegram idempotency | ✅ Done |

## P2 — Medium
| ID | Issue | Status |
|----|-------|--------|
| CR-010 | Persistent offset + atomic write | ✅ Done |
| CR-011 | Timezone Asia/Jakarta | ✅ Done |
| CR-012 | Fallback category lookup | ✅ Done |
| CR-013 | HTTP/JSON error handling | ✅ Done |
| CR-014 | Telegram Markdown escaping | ✅ Done |

## Files Changed
- `bot.py` — Authorization, ApiResult, validation, escaping, timezone, offset, category fixes
- `schema.sql` — Existing (triggers in migrations/)
- `migrations/001_fix_balance_trigger.sql` — CR-004 fix
- `migrations/002_add_idempotency.sql` — CR-009 unique index
- `tests/test_auth.py` — Authorization tests
- `tests/test_bot.py` — Baseline tests
- `docs/code-review/resolved.md` — This file

## Migration Commands (run manually)
```bash
# Balance trigger
psql $DATABASE_URL -f migrations/001_fix_balance_trigger.sql

# Idempotency index
psql $DATABASE_URL -f migrations/002_add_idempotency.sql
```

## Rollback Plan
```sql
-- CR-004: Restore from backup, trigger is idempotent
-- CR-009: DROP INDEX IF EXISTS idx_transactions_update_id;
```

## Test Results
```
Ran 5 tests in 0.007s — OK
- test_admin_authorized: passed
- test_unknown_rejected: passed
- test_admin_ids_is_list: passed
- test_bot_compiles: passed
- test_schema_readable: passed
```

## Final Status
✅ **14/14 CR resolved**
⚠️ SQL migrations NOT applied to production — need manual execution
⚠️ Systemd service needs `MASKAI_OFFSET_FILE` env var for persistent path
