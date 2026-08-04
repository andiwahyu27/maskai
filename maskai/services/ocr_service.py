"""MASKAI — OCR service (Tesseract + OpenCode Go)"""
import json, logging, re, os, subprocess, tempfile
from datetime import datetime
import requests

from maskai.config import config, TZ
from maskai.clients.telegram import send, tg
from maskai.clients.supabase import supabase_get, supabase_post
from maskai.utils.validation import parse_positive_amount
from maskai.utils.html import escape_html

log = logging.getLogger("maskai.services.ocr")

ALLOWED_OCR_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/octet-stream"}

SUFFIX_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/octet-stream": ".img",
}


def _get_fallback_category(user_id, tx_type):
    name = "Lainnya (Pemasukan)" if tx_type == "I" else "Lainnya (Pengeluaran)"
    for uid in (user_id, 0):
        result = supabase_get("maskai_categories", {
            "user_id": f"eq.{uid}", "name": f"ilike.{name}",
            "type": f"eq.{tx_type}", "select": "id", "limit": "1",
        })
        cats = result.data if result.ok and isinstance(result.data, list) else []
        if cats:
            return cats[0]["id"]
    return None


def extract_json_object(text):
    """Robust JSON extraction from AI response. Returns dict or None."""
    if not text or not isinstance(text, str):
        return None
    cleaned = re.sub(r'```(?:json)?\s*', '', text)
    cleaned = cleaned.replace('```', '').strip()
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        obj, _ = json.JSONDecoder().raw_decode(cleaned)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    start = cleaned.find('{')
    if start >= 0:
        end = cleaned.rfind('}')
        if end > start:
            try:
                obj = json.loads(cleaned[start:end + 1])
                if isinstance(obj, dict):
                    return obj
            except (json.JSONDecodeError, ValueError):
                pass
    return None


def _parse_tesseract_fallback(raw_text):
    """Simple regex fallback when AI parsing fails. Returns dict or None."""
    total_match = re.search(r'(?:total|jumlah|amount|sum)[^\d]*(\d[\d,.]+)', raw_text.lower())
    date_match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})', raw_text)
    result = {"toko": "Struk", "items": "-", "tanggal": date_match.group(1) if date_match else "?"}
    if total_match:
        result["total"] = str(int(total_match.group(1).replace(",", "").replace(".", "")))
        log.info("Fallback OCR result: %s", result)
        return result
    return None


def _download_telegram_image(file_path):
    try:
        url = f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{file_path}"
        r = requests.get(url, timeout=config.HTTP_TIMEOUT_LONG)
        if not 200 <= r.status_code < 300:
            log.error("Telegram file download failed status=%s", r.status_code)
            return False, None, None, "http_error"
        image_bytes = r.content
        if not image_bytes:
            return False, None, None, "empty_file"
        if len(image_bytes) > config.OCR_MAX_IMAGE_BYTES:
            return False, None, None, "too_large"
        content_type = (r.headers.get("Content-Type", "").split(";", 1)[0].strip().lower())
        if content_type not in ALLOWED_OCR_MIME_TYPES:
            log.warning("Unsupported OCR mime_type=%s", content_type or "missing")
            return False, None, None, "unsupported_mime"
        return True, image_bytes, content_type, None
    except requests.Timeout:
        return False, None, None, "timeout"
    except requests.ConnectionError:
        return False, None, None, "connection_error"
    except requests.RequestException as exc:
        log.error("Telegram file download failed error_type=%s", type(exc).__name__)
        return False, None, None, "request_exception"


def cmd_ocr(chat_id, user_id, file_id, update_id=None):
    """OCR — Tesseract for text extraction, OpenCode Go for JSON parsing"""
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

    # Tesseract with language fallback
    suffix = SUFFIX_BY_MIME.get(content_type, ".img")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
            tf.write(image_bytes)
            tmp_path = tf.name

        result = subprocess.run(
            ["tesseract", tmp_path, "stdout", "-l", "eng+ind"],
            capture_output=True, text=True, timeout=30,
        )
        log.info("Tesseract completed returncode=%s stdout_chars=%s stderr_chars=%s",
                 result.returncode, len(result.stdout or ""), len(result.stderr or ""))

        # If ind lang pack missing, retry with eng only
        if result.returncode != 0:
            log.warning("Tesseract eng+ind failed returncode=%s; retrying with eng", result.returncode)
            result = subprocess.run(
                ["tesseract", tmp_path, "stdout", "-l", "eng"],
                capture_output=True, text=True, timeout=30,
            )
            log.info("Tesseract eng fallback returncode=%s", result.returncode)

        if result.returncode != 0 or not result.stdout.strip():
            log.error("Tesseract failed returncode=%s stderr_length=%s",
                      result.returncode, len(result.stderr or ""))
            send(chat_id, "❌ Gagal membaca struk.")
            return

        raw_text = result.stdout.strip()
        log.info("Tesseract OCR: %s chars", len(raw_text))
    except (subprocess.TimeoutExpired, OSError) as e:
        log.error("Tesseract failed error_type=%s", type(e).__name__)
        send(chat_id, "❌ Gagal membaca struk.")
        return
    finally:
        image_bytes = None
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

    # Parse with AI
    from maskai.clients.dahono import claude
    prompt = (
        "Extract from this receipt OCR text. Return ONLY valid JSON:\n"
        '{"toko": "store name", "total": 12345, "items": "item list", "tanggal": "YYYY-MM-DD"}\n'
        "If unreadable: {\"error\": true}\n\nOCR Text:\n" + raw_text[:2000]
    )
    content = claude([{"role": "user", "content": prompt}], max_tokens=200)

    data = extract_json_object(content) if content else None

    if data is None:
        log.info("AI parsing unavailable; using regex fallback")
        data = _parse_tesseract_fallback(raw_text)

    if not isinstance(data, dict):
        send(chat_id, "❌ Struk tidak dapat dibaca.")
        return

    log.info("OCR parsing result ai_content=%s parsed=%s fallback=%s",
             bool(content), isinstance(data, dict), content is None)

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
    tx_payload = {
        "user_id": user_id, "type": "E", "amount": format(total, "f"),
        "category_id": fallback_cat,
        "description": f"{data.get('items', '-')} ({data.get('toko', 'Struk')})",
        "transaction_dt": data.get("tanggal", datetime.now(TZ).strftime("%Y-%m-%d")),
        "currency": "IDR",
    }
    log.info("OCR tx payload: cat=%s amt=%s dt=%s", tx_payload["category_id"], tx_payload["amount"], tx_payload["transaction_dt"])
    result = create_transaction(
        user_id=user_id, update_id=update_id,
        payload=tx_payload,
        source="ocr",
    )
    if result.status == CreateTransactionStatus.ALREADY_EXISTS:
        send(chat_id, "✅ Transaksi ini sudah pernah diproses sebelumnya.", parse_mode="HTML")
    elif result.status == CreateTransactionStatus.CREATED:
        send(chat_id,
             f"🛒 <b>{escape_html(data.get('toko', 'Struk'))}</b>\n"
             f"💰 Rp {total:,.0f}\n📋 {escape_html(data.get('items', '-'))}\n"
             f"📅 {escape_html(data.get('tanggal', '-'))}\n\n✅ Auto disimpan!",
             parse_mode="HTML")
    else:
        log.error("Transaction save failed status=%s error=%s", result.status, getattr(result, 'error', '?'))
        send(chat_id, "❌ Gagal menyimpan transaksi.")
