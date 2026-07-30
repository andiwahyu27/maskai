# MASKAI Deployment

## Server
- **Provider:** Tencent Cloud
- **IP:** 43.157.243.109
- **OS:** Ubuntu 24.04
- **User:** ubuntu

## Services

| Service | Type | Status |
|---------|------|--------|
| `maskai-bot.service` | systemd | Bot Telegram |
| `maskai-web.service` | systemd | Dashboard Flask |
| `caddy.service` | systemd | HTTPS proxy |

## Paths
```
/home/ubuntu/maskai/
├── bot.py              # Main bot
├── web/
│   ├── app.py          # Flask dashboard
│   └── templates/      # HTML templates
├── docs/               # Documentation
├── .env                # Secrets (git-ignored)
├── service-account.json# Google Sheets (git-ignored)
├── schema.sql          # DB schema
├── docker-compose.yml  # n8n (deprecated)
├── PRD.md              # Product requirements
└── auto-sync.sh        # Git auto-commit
```

## Caddy Config
```
/etc/caddy/Caddyfile

maskai.my.id → localhost:5678 (n8n, deprecated)
bot.maskai.my.id → localhost:5000 (dashboard)
```

## Environment Variables
`.env` file loaded by systemd via `EnvironmentFile`:

| Var | Desc |
|-----|------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Service role key |
| `BOT_TOKEN` | Telegram bot token |
| `DAHONO_KEY` | Dahono API key |
| `SECRET_KEY` | Flask session secret (random) |
| `ADMIN_PASSWORD` | Dashboard login |

## Cron Jobs

| Cron | Interval | Script |
|------|----------|--------|
| `maskai-sync` | 30m | `~/maskai/auto-sync.sh` → GitHub |
| `hermes-sync` | 30m | `~/sync_hermes.sh` → GitHub |

## Restart Commands
```bash
sudo systemctl restart maskai-bot.service    # Restart bot
sudo systemctl restart maskai-web.service    # Restart dashboard
sudo systemctl reload caddy                  # Reload HTTPS
```
