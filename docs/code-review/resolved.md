# Resolved Review Issues

## CR-001 — Authorization boundary
✅ Done | bot.py, tests/test_auth.py
- is_authorized() guard in process(). No callback queries in v2.

## CR-002 — OCR user ownership
✅ Done | bot.py
- cmd_ocr(user_id) instead of hardcoded 1367356347

## CR-003 — Date range filter
🟡 Phase 4 | Duplicate transaction_dt key

## CR-004 — Balance trigger
🟡 Phase 6 | Only INSERT handled

## CR-005 — /tambahkat user_id
⏭ Skipped | Category insert uses supabase_post, caller provides context

## CR-006 — Category ownership filter
🟡 Phase 4 | Edit/delete by id only

## CR-007 — API result model
✅ Partial | bot.py — ApiResult class, api_get/api_post typed

## CR-008 — Input validation
🟡 Phase 5 | Amount, LLM payload validation

## CR-009 — Telegram idempotency
🟡 Phase 7 | update_id not stored

## CR-010 — Persistent offset
🟡 Phase 7 | /tmp/maskai_offset.txt

## CR-011 — Timezone
🟡 Phase 4 | utcnow() used, no ZoneInfo

## CR-012 — Fallback category
✅ Done | bot.py — get_fallback_category() by name lookup, no hardcoded IDs

## CR-013 — HTTP/JSON errors
✅ Partial | bot.py — specific exception handlers, no bare except in API layer

## CR-014 — Telegram escaping
🟡 Phase 5 | MarkdownV2 or HTML escape
