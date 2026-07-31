"""MASKAI — OCR service"""
import json, logging, re, requests
from datetime import datetime
from maskai.config import config, DAHONO_URL, DAHONO_KEY, TZ, BOT_TOKEN
from maskai.clients.telegram import send, tg
from maskai.clients.supabase import supabase_get, supabase_post
from maskai.utils.validation import parse_positive_amount
from maskai.utils.html import escape_html
from maskai.app import get_fallback_category

log = logging.getLogger("maskai.services.ocr")

def cmd_ocr(chat_id, user_id, file_id, update_id=None):
    """OCR using GPT-5.5 Vision"""
    info = tg("getFile", {"file_id": file_id})
    if not info.get("ok"):
        send(chat_id, "Gagal download foto")
        return
    path = info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"

    send(chat_id, "⏳ Membaca struk...")

    payload = {
        "model": "dahono/gpt-5.5",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Extract from this receipt/store invoice. Return ONLY valid JSON, no other text:\n{\"toko\": \"store name\", \"total\": 12345, \"items\": \"item list\", \"tanggal\": \"YYYY-MM-DD\"}\nIf unreadable: {\"error\": true}"},
            {"type": "image_url", "image_url": {"url": url}}
        ]}],
        "max_tokens": 300
    }

    try:
        r = requests.post(f"{DAHONO_URL}/chat/completions", json=payload,
            headers={"Authorization": f"Bearer {DAHONO_KEY}", "Content-Type": "application/json"}, timeout=config.HTTP_TIMEOUT_LONG)
        if r.status_code != 200 or not r.text:
            log.error(f"OCR error {r.status_code}: {r.text[:200] if r.text else 'empty'}")
            send(chat_id, "❌ Gagal membaca struk.")
            return
    except requests.Timeout:
        log.error("OCR request timeout")
        send(chat_id, "❌ OCR timeout. Coba lagi.")
        return
    except requests.ConnectionError:
        log.error("OCR connection error")
        send(chat_id, "❌ Gagal terhubung ke OCR.")
        return
    except requests.RequestException as exc:
        log.error("OCR request failed: %s", exc)
        send(chat_id, "❌ Layanan OCR sedang bermasalah.")
        return

    try:
        content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except (ValueError, KeyError, IndexError, TypeError):
        log.error(f"OCR invalid response: {r.text[:200]}")
        send(chat_id, "❌ Format hasil OCR tidak valid.")
        return

    if not content:
        send(chat_id, "❌ Struk tidak dapat dibaca.")
        return

    try:
        data = json.loads(re.sub(r"```json|```", "", content).strip())
    except (json.JSONDecodeError, ValueError):
        log.error(f"OCR parse: {content[:200]}")
        send(chat_id, "❌ Struk tidak dapat dibaca.")
        return

    # Validate OCR response is a dict
    if not isinstance(data, dict):
        log.error(f"OCR response not dict: {type(data).__name__}")
        send(chat_id, "❌ Format hasil OCR tidak valid.")
        return

    if data.get("error"):
        send(chat_id, "❌ Struk tidak jelas. Coba foto ulang.")
        return

    # Validate OCR amount using shared parser
    total, err = parse_positive_amount(data.get("total"))
    if err:
        send(chat_id, f"❌ Jumlah di struk tidak valid: {err}")
        return

    fallback_cat = get_fallback_category(user_id, "E")
    if not fallback_cat:
        send(chat_id, "❌ Gagal menyimpan — kategori default tidak ditemukan.")
        return

    result = supabase_post("maskai_transactions", {
        "user_id": user_id, "type": "E", "amount": format(total, "f"),
        "category_id": fallback_cat, "description": f"{data.get('items','-')} ({data.get('toko','Struk')})",
        "transaction_dt": data.get("tanggal", datetime.now(TZ).strftime("%Y-%m-%d")), "currency": "IDR",
        "metadata": {"telegram_update_id": str(update_id), "source": "ocr"} if update_id else None
    })
    if result.ok:
        send(chat_id, f"🛒 <b>{escape_html(data.get('toko','Struk'))}</b>\n💰 Rp {total:,.0f}\n📋 {escape_html(data.get('items','-'))}\n📅 {escape_html(data.get('tanggal','-'))}\n\n✅ Auto disimpan!", parse_mode="HTML")
    else:
        send(chat_id, "❌ Gagal menyimpan transaksi.")
