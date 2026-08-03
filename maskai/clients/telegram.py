"""MASKAI — Telegram API client"""
import logging
from maskai.clients.http import api_get, api_post
from maskai.config import config

log = logging.getLogger("maskai.tg")


def tg(method, data=None):
    """Telegram API call"""
    url = f"{config.TELEGRAM_API}/{method}"
    if data:
        result = api_post(url, json=data)
    else:
        result = api_get(url)
    return result.data if result.ok else {"ok": False, "error": result.error}


def send(chat_id, text, parse_mode=None, reply_markup=None):
    """Send Telegram message"""
    d = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        d["parse_mode"] = parse_mode
    if reply_markup:
        d["reply_markup"] = reply_markup
    return tg("sendMessage", d)
