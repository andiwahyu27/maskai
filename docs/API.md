# MASKAI API Reference

## External APIs Used

### Dahono (LLM Gateway)
- **Base URL:** `https://gateway.dahono.com/v1`
- **Auth:** Bearer token via `DAHONO_KEY` env

| Model | Use | Vision |
|-------|-----|--------|
| `dahono/claude-sonnet-4.5-free` | Text parsing | ❌ |
| `dahono/gpt-5.5` | OCR receipt | ✅ |

### Telegram Bot API
- **Base URL:** `https://api.telegram.org/bot<TOKEN>/`
- **Methods used:** `getUpdates`, `sendMessage`, `getFile`, `answerCallbackQuery`
- **Polling interval:** 30s long-poll

### Supabase REST API
- **Base URL:** `https://<ref>.supabase.co/rest/v1/`
- **Auth Headers:** `apikey` + `Authorization: Bearer` (service_role)
- **Tables:** `maskai_transactions`, `maskai_categories`, `maskai_debts`, `maskai_keranjang`, `maskai_balance`

### Google Sheets API
- **Auth:** Service Account (`/home/ubuntu/maskai/service-account.json`)
- **Sheet ID:** `1dBkYHEGsftjqH2NA9bd5EJ58Cc_HYKt8rVoWk0RdQUg`
- **Library:** `gspread`

## Internal API (Dashboard)

Dashboard Flask API at `bot.maskai.my.id`:

| Route | Method | Auth | Desc |
|-------|--------|------|------|
| `/api/status` | GET | Session | Bot status + stats |
| `/api/transactions` | GET | Session | All transactions |
| `/api/categories` | GET | Session | All categories |
| `/api/categories` | POST | Session | Add category |
| `/api/categories` | PUT | Session | Update category |
| `/api/categories?id=` | DELETE | Session | Delete category |
| `/api/settings` | GET | Session | Current settings |
| `/api/settings` | POST | Session | Save settings |
| `/api/logs?lines=&level=` | GET | Session | Bot logs |
| `/api/sync` | GET | Session | Sync to Sheets |
| `/api/restart` | POST | Session | Restart bot |
