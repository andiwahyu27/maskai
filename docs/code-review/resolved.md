# Resolved Review Issues

## CR-001 — Authorization boundary
✅ Done | bot.py, tests/test_auth.py
is_authorized() guard in process().

## CR-002 — OCR user ownership
✅ Done | bot.py
cmd_ocr(user_id), no hardcoded admin ID.

## CR-003 — Date range filter
✅ Done | bot.py
supabase_get accepts list of tuples for duplicate keys.

## CR-004 — Balance trigger
⏸ Deferred | Requires SQL migration. Manual review needed.

## CR-005 — /tambahkat user_id
⏭ Skipped | Category insert uses caller context.

## CR-006 — Category ownership filter
🟡 | Edit/delete by id only. Low risk for single-user bot.

## CR-007 — API result model
✅ Done | bot.py
ApiResult class, typed api_get/api_post.

## CR-008 — Input validation
✅ Done | bot.py
parse_positive_amount() validates before insert.

## CR-009 — Telegram idempotency
⏸ Deferred | Requires schema change (unique index).

## CR-010 — Persistent offset
🟡 | /tmp path, survives reboot on this VPS.

## CR-011 — Timezone
🟡 | Still uses utcnow(). Low impact since dates come from user input.

## CR-012 — Fallback category
✅ Done | bot.py
get_fallback_category() by name lookup.

## CR-013 — HTTP/JSON errors
✅ Done | bot.py
Specific exception handlers, no bare except.

## CR-014 — Telegram escaping
✅ Done | bot.py
escape_md() applied to all dynamic content.
