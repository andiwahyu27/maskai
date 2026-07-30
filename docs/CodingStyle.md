# MASKAI Coding Style

## Python (bot.py + web/app.py)

### Naming
- **Functions:** `snake_case` — `cmd_laporan()`, `supabase_get()`
- **Constants:** `UPPER_CASE` — `SUPABASE_URL`, `ADMIN_IDS`
- **Variables:** `snake_case` — `chat_id`, `user_id`, `tx_type`

### Error Handling
```python
# Good - catch specific
try:
    r = requests.get(url, timeout=10)
    return r.json()
except requests.Timeout:
    log.error("Timeout")
    return None
except Exception as e:
    log.error(f"Unexpected: {e}")
    return None
```

### API Calls
- Semua external API call MUST punya timeout
- Semua response JSON MUST di-try/except
- Log error dengan context secukupnya

### Telemetry
```python
log.info("Starting process...")     # Flow penting
log.warning("Retry 3/5")            # Recovery
log.error(f"Claude API: {code}")    # Error dengan detail
log.critical("Bot stopping")        # Fatal
```

### Anti-patterns
```python
# ❌ Jangan
r.json()                           # No try-except
requests.get(url)                  # No timeout

# ✅ Harus
try: r = requests.get(url, timeout=10); return r.json()
except: return None
```

## HTML Templates
- Alpine.js untuk reactivity
- CSS internal (no CDN)
- Mobile-first responsive
- SVG icons (no emoji di UI elements)

## File Organization
```
bot.py              # Flat structure — all in one file
web/
  app.py            # Flask routes + logic
  templates/        # Jinja2 HTML
    base.html       # Navbar + layout
    *.html          # Pages
```
Rule of thumb: jangan extract ke file terpisah sampai file >1000 baris.

## Git
- Commit message: bahasa Indonesia
- Format: `<verb> <description>`
- Contoh: `Fix OCR model`, `Add /menu command`
- Jangan commit `.env`, `service-account.json`, `__pycache__/`
