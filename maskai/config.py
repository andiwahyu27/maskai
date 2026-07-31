"""MASKAI — Centralized Configuration"""
import os, sys
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

@dataclass(frozen=True)
class Config:
    """All configuration from environment"""
    BOT_TOKEN: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    DAHONO_KEY: str
    DAHONO_URL: str = "https://gateway.dahono.com/v1"
    TELEGRAM_API: str = ""
    SUPABASE_HEADERS: dict = field(default_factory=dict)
    HTTP_TIMEOUT: int = 15
    HTTP_TIMEOUT_LONG: int = 30
    HTTP_TIMEOUT_SHORT: int = 5
    POLL_TIMEOUT: int = 35
    TZ: ZoneInfo = ZoneInfo("Asia/Jakarta")
    LOG_LEVEL: str = "INFO"
    OFFSET_FILE: str = "/var/lib/maskai-bot/offset.txt"
    GOOGLE_CREDS_FILE: str = ""
    GOOGLE_SHEET_ID: str = ""
    ADMIN_IDS: list = field(default_factory=lambda: [1367356347])

    def __post_init__(self):
        missing = [k for k in ("BOT_TOKEN","SUPABASE_URL","SUPABASE_KEY","DAHONO_KEY") if not getattr(self,k)]
        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

def from_env():
    tz_str = os.environ.get("TZ", "Asia/Jakarta")
    token = os.environ.get("BOT_TOKEN", "")
    return Config(
        BOT_TOKEN=token,
        SUPABASE_URL=os.environ.get("SUPABASE_URL", ""),
        SUPABASE_KEY=os.environ.get("SUPABASE_KEY", ""),
        DAHONO_KEY=os.environ.get("DAHONO_KEY", ""),
        TELEGRAM_API=f"https://api.telegram.org/bot{token}",
        SUPABASE_HEADERS={"apikey": os.environ.get("SUPABASE_KEY",""), "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY','')}", "Content-Type": "application/json"},
        TZ=ZoneInfo(tz_str),
        LOG_LEVEL=os.environ.get("LOG_LEVEL","INFO"),
        OFFSET_FILE=os.environ.get("MASKAI_OFFSET_FILE","/var/lib/maskai-bot/offset.txt"),
        GOOGLE_CREDS_FILE=os.environ.get("GOOGLE_CREDS_FILE",""),
        GOOGLE_SHEET_ID=os.environ.get("GOOGLE_SHEET_ID",""),
    )

_config = None
def get_config():
    global _config
    if _config is None:
        try:
            _config = from_env()
        except RuntimeError as e:
            if __name__ == "__main__":
                print(f"FATAL: {e}", file=sys.stderr)
                sys.exit(1)
            _config = Config(BOT_TOKEN="test", SUPABASE_URL="test", SUPABASE_KEY="test", DAHONO_KEY="test")
    return _config

config = get_config()
# Backward compat aliases
SUPABASE_URL = config.SUPABASE_URL
SUPABASE_KEY = config.SUPABASE_KEY
BOT_TOKEN = config.BOT_TOKEN
DAHONO_KEY = config.DAHONO_KEY
DAHONO_URL = config.DAHONO_URL
TELEGRAM_API = config.TELEGRAM_API
SUPABASE_HEADERS = config.SUPABASE_HEADERS
TZ = config.TZ
JAKARTA_TZ = ZoneInfo("Asia/Jakarta")
ADMIN_IDS = config.ADMIN_IDS
