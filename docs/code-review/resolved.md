# Resolved Review Issues

## CR-001 — Authorization boundary
✅ Done | bot.py, tests/test_auth.py
is_authorized() guard in process(). No callback queries in v2.

## CR-002 — OCR user ownership
✅ Done | bot.py
cmd_ocr(user_id), no hardcoded admin ID.

## CR-003 — Date range filter
✅ Done | bot.py
supabase_get accepts list of tuples for duplicate keys. Date range now sends both gte+lte.

## CR-004 — Balance trigger
🟡 Phase 6 | Only INSERT handled

## CR-005 — /tambahkat user_id
⏭ Skipped | Category insert uses caller context

## CR-006 — Category ownership filter
🟡 Phase 4 | Edit/delete by id only — needs user_id filter in callback

## CR-007 — API result model
✅ Done | bot.py
ApiResult class, api_get/api_post typed, supabase_get/post wrap result.

## CR-008 — Input validation
🟡 Phase 5 | Amount, LLM payload validation

## CR-009 — Telegram idempotency
🟡 Phase 7 | update_id not stored

## CR-010 — Persistent offset
🟡 Phase 7 | /tmp/maskai_offset.txt

## CR-011 — Timezone
🟡 Phase 4 | utcnow() used, no ZoneInfo for laporan periods

## CR-012 — Fallback category
✅ Done | bot.py
get_fallback_category() by name lookup.

## CR-013 — HTTP/JSON errors
✅ Done | bot.py
Specific exception handlers in api_get/api_post.

## CR-014 — Telegram escaping
🟡 Phase 5 | MarkdownV2 or HTML escape
