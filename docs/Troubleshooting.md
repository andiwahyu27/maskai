# MASKAI Troubleshooting

## Bot tidak merespon
```bash
# Cek status
sudo systemctl status maskai-bot.service

# Cek log
sudo journalctl -u maskai-bot.service -n 50

# Restart
sudo systemctl restart maskai-bot.service
```

Penyebab umum:
- Webhook conflict → `curl https://api.telegram.org/bot<TOKEN>/deleteWebhook`
- Token expired → cek `.env` file
- Claude API down → cek `https://gateway.dahono.com/v1/models`

## Dashboard 403 / 502
```bash
sudo systemctl status maskai-web.service caddy
sudo systemctl restart maskai-web.service
```

## OCR tidak bisa baca
- `dahono/claude-sonnet-4.5-free` TIDAK support vision
- Pastikan model OCR = `dahono/gpt-5.5`
- Cek log: `journalctl -u maskai-bot.service | grep -i ocr`

## Supabase error "Expecting value"
Normal untuk POST response (201 tanpa body). Sudah di-handle oleh error handling.

## Duplikat transaksi
Saat restart bot, offset disimpan per-update untuk mencegah duplikasi.
Jika masih terjadi, reset offset: `echo "0" > /tmp/maskai_offset.txt`

## Bot loop restart (/stop)
`/stop` sekarang graceful shutdown — offset disimpan sebelum exit.
Jika masih loop: hapus offset file + delete webhook pending updates.

## GitHub push ditolak
- Token PAT expired → update di `~/.git-credentials`
- Force push conflicts → `git pull --rebase` dulu

## Memory/CPU tinggi
- Bot: ~30MB RAM (Python long-polling)
- Dashboard: ~30MB RAM (Flask dev server)
- Caddy: minimal
- Jika >100MB, cek `htop` untuk process zombie
