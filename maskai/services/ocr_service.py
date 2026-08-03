"""MASKAI — OCR service"""
import json, logging, re, requests
from datetime import datetime
from maskai.config import config, DAHONO_URL, DAHONO_KEY, TZ, BOT_TOKEN
from maskai.clients.telegram import send, tg
from maskai.clients.supabase import supabase_get, supabase_post
from maskai.utils.validation import parse_positive_amount
from maskai.utils.html import escape_html
from maskai.utils.logging_utils import safe_body_for_log

log = logging.getLogger("maskai.services.ocr")

def _get_fallback_category(user_id, tx_type):
    """Lookup fallback category"""
    name = "Lainnya (Pemasukan)" if tx_type == "I" else "Lainnya (Pengeluaran)"
    for uid in (user_id, 0):
        result = supabase_get("maskai_categories", {"user_id": f"eq.{uid}", "name": f"ilike.{name}", "type": f"eq.{tx_type}", "select": "id", "limit": "1"})
        cats = result.data if result.ok and isinstance(result.data, list) else []
        if cats:
            return cats[0]["id"]
    return None

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
            log.error("OCR error status=%s body=%s", r.status_code, safe_body_for_log(r.text, 80))
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
        log.error("OCR invalid response: %s", safe_body_for_log(r.text, 80))
        send(chat_id, "❌ Format hasil OCR tidak valid.")
        return

    if not content:
        send(chat_id, "❌ Struk tidak dapat dibaca.")
        return

    try:
        data = json.loads(re.sub(r"```json|```", "", content).strip())
    except (json.JSONDecodeError, ValueError):
        log.error("OCR parse failed len=%s", len(content))
        send(chat_id, "❌ Struk tidak dapat dibaca.")
        return

    # Validate OCR response is a dict
    if not isinstance(data, dict):
        log.error("OCR response not dict: %s", type(data).__name__)
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

    fallback_cat = _get_fallback_category(user_id, "E")
    if not fallback_cat:
        send(chat_id, "❌ Gagal menyimpan — kategori default tidak ditemukan.")
        return

    from maskai.repositories.transaction_repository import create_transaction, CreateTransactionStatus
    result = create_transaction(
        user_id=user_id,
        update_id=update_id,
        payload={
            "user_id": user_id, "type": "E", "amount": format(total, "f"),
            "category_id": fallback_cat, "description": f"{data.get('items','-')} ({data.get('toko','Struk')})",
            "transaction_dt": data.get("tanggal", datetime.now(TZ).strftime("%Y-%m-%d")), "currency": "IDR",
        },
        source="ocr",
    )
    if result.status in (CreateTransactionStatus.CREATED, CreateTransactionStatus.ALREADY_EXISTS):
        if result.status == CreateTransactionStatus.ALREADY_EXISTS:
            send(chat_id, "✅ Transaksi ini sudah pernah diproses sebelumnya.", parse_mode="HTML")
        else:
            send(chat_id, f"🛒 <b>{escape_html(data.get('toko','Struk'))}</b>\n💰 Rp {total:,.0f}\n📋 {escape_html(data.get('items','-'))}\n📅 {escape_html(data.get('tanggal','-'))}\n\n✅ Auto disimpan!", parse_mode="HTML")
    else:
        send(chat_id, "❌ Gagal menyimpan transaksi.")
