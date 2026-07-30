# MASKAI Architecture

## Overview
MASKAI adalah AI-powered Telegram bot untuk tracking keuangan pribadi. 
Input bisa natural language ("beli telur 20rb") atau foto struk (OCR).

## Stack
```
┌─────────────┐    ┌──────────────┐    ┌────────────┐
│  Telegram   │───▶│  VPS Ubuntu   │───▶│  Supabase  │
│  @maskaion  │    │  43.157.x.x   │    │  PostgreSQL│
└─────────────┘    └──────┬───────┘    └────────────┘
                          │
                  ┌───────┴───────┐
                  │  Dahono API   │────▶ Claude Sonnet (teks)
                  │  GPT-5.5      │────▶ OCR struk
                  └───────────────┘
                          │
                  ┌───────┴───────┐
                  │  Google APIs  │────▶ Google Sheets
                  │  Caddy        │────▶ HTTPS proxy
                  └───────────────┘
```

## Data Flow
1. User kirim pesan/foto ke Telegram @maskaionBot
2. Bot polling `getUpdates` tiap 30 detik
3. Teks → Claude Sonnet 4.5 (via Dahono) → parsing intent + jumlah + kategori
4. Foto → di-download → base64 → GPT-5.5 (via Dahono) → OCR
5. Hasil parsing disimpan ke Supabase PostgreSQL
6. Bot reply ke user dengan konfirmasi

## Components
| Komponen | Tech | Lokasi |
|----------|------|--------|
| Bot utama | Python 3.11 | `/home/ubuntu/maskai/bot.py` |
| Service | systemd | `maskai-bot.service` |
| Dashboard | Flask + Alpine.js | `/home/ubuntu/maskai/web/` |
| Dashboard service | systemd | `maskai-web.service` |
| HTTPS | Caddy | `/etc/caddy/Caddyfile` |
| Cron backup | cron | `/etc/cron.d/maskai-sync` |
| Hermes sync | cron | `/etc/cron.d/hermes-sync` |

## Domains
- `maskai.my.id` → n8n (port 5678, deprecated)  
- `bot.maskai.my.id` → Dashboard Flask (port 5000)
