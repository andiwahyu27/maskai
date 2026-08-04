"""MASKAI — OCR service (V2-SEC-001: secure image transfer)"""
import json, logging, re, os, subprocess, tempfile
from datetime import datetime
import requests

from maskai.config import config, DAHONO_URL, DAHONO_KEY, TZ, BOT_TOKEN
from maskai.clients.telegram import send, tg
from maskai.clients.supabase import supabase_get, supabase_post
from maskai.utils.validation import parse_positive_amount
from maskai.utils.html import escape_html

log = logging.getLogger("maskai.services.ocr")

ALLOWED_OCR_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/octet-stream"}


def _get_fallback_category(user_id, tx_type):
    name = "Lainnya (Pemasukan)" if tx_type == "I" else "Lainnya (Pengeluaran)"
    for uid in (user_id, 0):
        result = supabase_get("maskai_categories", {"user_id": f"eq.{uid}", "name": f"ilike.{name}", "type": f"eq.{tx_type}", "select": "id", "limit": "1"})
        cats = result.data if result.ok and isinstance(result.data, list) else []
        if cats:
            return cats[0]["id"]
    return None


def _download_telegram_image(file_path):
    """Download image from Telegram. Returns (ok, image_bytes, content_type, error_code). BOT_TOKEN never leaves this function."""
    try:
        url = f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{file_path}"
        r = requests.get(url, timeout=config.HTTP_TIMEOUT_LONG)
        if not 200 <= r.status_code < 300:
            log.error("Telegram file download failed status=%s", r.status_code)
            return False, None, None, "http_error"
        image_bytes = r.content
        if not image_bytes:
            log.error("Telegram file download: empty body")
            return False, None, None, "empty_file"
        if len(image_bytes) > config.OCR_MAX_IMAGE_BYTES:
            log.error("Telegram file too large: %s bytes", len(image_bytes))
            return False, None, None, "too_large"
        content_type = (r.headers.get("Content-Type", "").split(";", 1)[0].strip().lower())
        if content_type not in ALLOWED_OCR_MIME_TYPES:
            log.warning("Unsupported OCR mime_type=%s", content_type or "missing")
            return False, None, None, "unsupported_mime"
        return True, image_bytes, content_type, None
    except requests.Timeout:
        log.error("Telegram file download timeout")
        return False, None, None, "timeout"
    except requests.ConnectionError:
        log.error("Telegram file download connection error")
        return False, None, None, "connection_error"
    except requests.RequestException as exc:
        log.error("Telegram file download failed error_type=%s", type(exc).__name__)
        return False, None, None, "request_exception"


def _encode_as_data_url(image_bytes, content_type):
    """Encode raw bytes as base64 data URL"""
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{content_type};base64,{encoded}"
    # Clear references
    encoded = None
    return data_url


def cmd_ocr(chat_id, user_id, file_id, update_id=None):
    """OCR — downloads image locally, sends base64 to Dahono. ZERO BOT_TOKEN in external payload."""
    info = tg("getFile", {"file_id": file_id})
    if not info.get("ok"):
        send(chat_id, "❌ Gagal mengunduh gambar dari Telegram.")
        return
    path = info["result"]["file_path"]

    send(chat_id, "⏳ Membaca struk...")

    ok, image_bytes, content_type, err_code = _download_telegram_image(path)
    if not ok:
        if err_code == "too_large":
            send(chat_id, "❌ Ukuran gambar terlalu besar.")
        elif err_code == "unsupported_mime":
            send(chat_id, "❌ Format gambar tidak didukung.")
        else:
            send(chat_id, "❌ Gagal mengunduh gambar dari Telegram.")
        return

    log.info("OCR image prepared mime_type=%s size_bytes=%s", content_type, len(image_bytes))

    # Tesseract OCR — local, no API call needed
    import subprocess, tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(image_bytes)
            tmp_path = tf.name
        result = subprocess.run(["tesseract", tmp_path, "stdout", "-l", "eng+ind"],
            capture_output=True, text=True, timeout=30)
        os.unlink(tmp_path)
        raw_text = result.stdout.strip()
        if not raw_text:
            log.error("Tesseract returned empty")
            send(chat_id, "❌ Struk tidak dapat dibaca.")
            return
        log.info("Tesseract OCR: %s chars", len(raw_text))
    except (subprocess.TimeoutExpired, OSError) as e:
        log.error("Tesseract failed error_type=%s", type(e).__name__)
        send(chat_id, "❌ Gagal membaca struk.")
        return
    finally:
        image_bytes = None

    # Parse with Claude text model
    from maskai.clients.dahono import claude
    prompt = f"Extract from this receipt OCR text. Return ONLY valid JSON:\n{{\"toko\": \"store name\", \"total\": 12345, \"items\": \"item list\", \"tanggal\": \"YYYY-MM-DD\"}}\nIf unreadable: {{\"error\": true}}\n\nOCR Text:\n{raw_text[:2000]}"
    content = claude([{"role": "user", "content": prompt}], max_tokens=200)
    if not content:
        # Fallback: try simple regex parsing
        content = _parse_tesseract_fallback(raw_text)
        if not content:
            send(chat_id, "❌ Struk tidak dapat dibaca.")
            return

    try:
        data = json.loads(re.sub(r"```json|```", "", content).strip())
    except (json.JSONDecodeError, ValueError):
        log.error("Claude parse failed length=%s", len(content))
        send(chat_id, "❌ Struk tidak dapat dibaca.")
        return
    if not isinstance(data, dict):
        log.error("Claude response not dict: %s", type(data).__name__)
        send(chat_id, "❌ Format hasil OCR tidak valid.")
        return
    if not content:
        send(chat_id, "❌ Struk tidak dapat dibaca.")
        return

    if data.get("error"):
        send(chat_id, "❌ Struk tidak jelas. Coba foto ulang.")
        return

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
        user_id=user_id, update_id=update_id,
        payload={
            "user_id": user_id, "type": "E", "amount": format(total, "f"),
            "category_id": fallback_cat, "description": f"{data.get('items','-')} ({data.get('toko','Struk')})",
            "transaction_dt": data.get("tanggal", datetime.now(TZ).strftime("%Y-%m-%d")), "currency": "IDR",
        },
        source="ocr",
    )
    if result.status == CreateTransactionStatus.ALREADY_EXISTS:
        send(chat_id, "✅ Transaksi ini sudah pernah diproses sebelumnya.", parse_mode="HTML")
    elif result.status == CreateTransactionStatus.CREATED:
        send(chat_id, f"🛒 <b>{escape_html(data.get('toko','Struk'))}</b>\n💰 Rp {total:,.0f}\n📋 {escape_html(data.get('items','-'))}\n📅 {escape_html(data.get('tanggal','-'))}\n\n✅ Auto disimpan!", parse_mode="HTML")
    else:
        log.error("Transaction save failed status=%s error=%s", result.status, getattr(result, 'error', '?'))
        send(chat_id, "❌ Gagal menyimpan transaksi.")


def _parse_tesseract_fallback(raw_text):
    """Simple regex fallback when Claude is unavailable"""
    import re
    total_match = re.search(r'(?:total|jumlah|amount|sum)[^\d]*(\d[\d,.]+)', raw_text.lower())
    date_match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})', raw_text)
    result = {"toko": "Struk", "items": "-", "tanggal": date_match.group(1) if date_match else "?"}
    if total_match:
        result["total"] = str(int(total_match.group(1).replace(",", "").replace(".", "")))
        log.info("Fallback OCR result: %s", result)
        return json.dumps(result)
    return None
