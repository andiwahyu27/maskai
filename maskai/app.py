"""MASKAI v2 — Application orchestration (CR-003)"""
import os, sys, json, logging, time as time_module
from datetime import datetime
import requests

# ── Modular imports ──
from maskai.config import config, SUPABASE_URL, SUPABASE_KEY, BOT_TOKEN, DAHONO_KEY
from maskai.config import DAHONO_URL, TELEGRAM_API, SUPABASE_HEADERS, TZ, ADMIN_IDS
from maskai.utils.html import escape_html
from maskai.utils.offset_store import OffsetStore
from maskai.clients.telegram import send
from maskai.clients.supabase import supabase_get, supabase_post, supabase_patch, supabase_delete
from maskai.repositories.category_repository import get_accessible_category, delete_owned_category
from maskai.state.pending_store import pending

# ── Imports from handler/service modules ──
from maskai.handlers.command_handlers import (
    cmd_start, cmd_laporan, cmd_kategori, cmd_editkat, cmd_hapuskat, cmd_tambahkat,
    cmd_saldo, cmd_debt, cmd_keranjang, cmd_natural, cmd_status, cmd_usage
)
from maskai.services.ocr_service import cmd_ocr

# ── Logging ──
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("maskai")
BOT_START_TIME = time_module.time()

# ── Auth ──
def is_authorized(user_id):
    return user_id in ADMIN_IDS

def log_security(action, user_id, detail=""):
    log.warning(f"SECURITY | {action} | user={user_id} | {detail}")

# ── Shared helper ──
def get_fallback_category(user_id, tx_type):
    """Lookup fallback category by name and type"""
    name = "Lainnya (Pemasukan)" if tx_type == "I" else "Lainnya (Pengeluaran)"
    for uid in (user_id, 0):
        result = supabase_get("maskai_categories", {"user_id": f"eq.{uid}", "name": f"ilike.{name}", "type": f"eq.{tx_type}", "select": "id", "limit": "1"})
        cats = result.data if result.ok and isinstance(result.data, list) else []
        if cats:
            return cats[0]["id"]
    return None

# ── Router ──
def process(msg, update_id=None):
    chat_id = msg.get("chat", {}).get("id")
    user_id = msg.get("from", {}).get("id", 0)
    text = (msg.get("text", "") or msg.get("caption", "")).strip()
    photo = msg.get("photo")

    if not is_authorized(user_id):
        log_security("denied", user_id)
        return

    if photo:
        cmd_ocr(chat_id, user_id, photo[-1]["file_id"], update_id)
        return

    if not text:
        return

    # Command dispatch
    cmd = text.lower().split()[0] if text else ""
    args = text

    if cmd in ("/start", "/help", "/menu"):
        cmd_start(chat_id)
    elif cmd == "/kategori":
        cmd_kategori(chat_id, user_id)
    elif cmd == "/editkat":
        cmd_editkat(chat_id, user_id, args)
    elif cmd == "/hapuskat":
        cmd_hapuskat(chat_id, user_id, args)
    elif cmd == "/tambahkat":
        cmd_tambahkat(chat_id, user_id, args)
    elif cmd in ("/laporan", "/report", "/r"):
        cmd_laporan(chat_id, user_id, args)
    elif cmd in ("/saldo", "/balance"):
        cmd_saldo(chat_id, user_id)
    elif cmd in ("/hutang", "/piutang"):
        cmd_debt(chat_id, user_id, args)
    elif cmd == "/keranjang":
        cmd_keranjang(chat_id, user_id, args)
    elif cmd == "/status":
        cmd_status(chat_id, user_id)
    elif cmd in ("/usage", "/cekdb"):
        cmd_usage(chat_id)
    elif cmd == "/sync":
        _cmd_sync(chat_id, user_id)
    elif cmd == "/resetdb":
        _cmd_resetdb(chat_id, user_id)
    elif cmd == "/stop":
        if user_id in ADMIN_IDS:
            return "__STOP__"
    elif text:
        # Check pending state first
        p = pending.get(chat_id, user_id)
        if p:
            _handle_pending(chat_id, user_id, text, p)
        else:
            cmd_natural(chat_id, user_id, text, update_id)

# ── Sync & Reset (inline, simple) ──
def _cmd_sync(chat_id, user_id):
    if not config.GOOGLE_CREDS_FILE or not config.GOOGLE_SHEET_ID:
        send(chat_id, "❌ Konfigurasi Google Sheets belum lengkap.")
        return
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_CREDS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID).sheet1
        tx_result = supabase_get("maskai_transactions", {"select": "id,type,amount,description,transaction_dt,created_at,category_id", "order": "id.asc"})
        txs = tx_result.data if tx_result.ok and isinstance(tx_result.data, list) else []
        cat_result = supabase_get("maskai_categories", {"select": "id,name"})
        cat_list = cat_result.data if cat_result.ok and isinstance(cat_result.data, list) else []
        cats = {c["id"]: c["name"] for c in cat_list}
        if not txs:
            send(chat_id, "❌ Tidak ada transaksi.")
            return
        sheet.clear()
        sheet.append_row(["ID", "Tanggal", "Tipe", "Jumlah", "Kategori", "Deskripsi"])
        for t in txs:
            cat_name = escape_html(cats.get(t.get("category_id"), "Lainnya"))
            sheet.append_row([
                t["id"], t.get("transaction_dt", ""),
                "Masuk" if t["type"] == "I" else "Keluar",
                t["amount"], cat_name,
                escape_html(t.get("description", "-"))
            ])
        send(chat_id, f"✅ Sinkronisasi selesai. {len(txs)} baris ke Google Sheets.")
    except Exception as e:
        log.exception("Google Sheets sync failed user_id=%s", user_id)
        send(chat_id, "❌ Sinkronisasi gagal. Silakan coba lagi.")

def _cmd_resetdb(chat_id, user_id):
    if not is_authorized(user_id):
        send(chat_id, "❌ Hanya admin yang bisa.")
        return
    failed = []
    for table in ["maskai_transactions", "maskai_debts", "maskai_keranjang"]:
        result = supabase_delete(table, "user_id", user_id)
        if not result.ok:
            failed.append(table)
    if failed:
        send(chat_id, f"⚠️ Sebagian gagal: {', '.join(failed)}")
    else:
        send(chat_id, "✅ Database dikosongkan.")

def _handle_pending(chat_id, user_id, text, p):
    """Handle pending date response"""
    p = pending.pop(chat_id, user_id)
    if not p:
        return
    tgl = None
    t = text.strip().lower()
    from datetime import datetime
    if t in ("hari ini", "today"):
        tgl = datetime.now(TZ).strftime("%Y-%m-%d")
    elif t in ("kemarin", "yesterday"):
        tgl = (datetime.now(TZ) - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(text, fmt)
                tgl = dt.strftime("%Y-%m-%d")
                break
            except (ValueError, IndexError):
                pass
    if not tgl:
        send(chat_id, "❌ Format tanggal tidak dikenali.")
        return
    from maskai.utils.validation import parse_positive_amount
    amount = p.get("amount")
    if not isinstance(amount, __import__('decimal').Decimal):
        amount, err = parse_positive_amount(amount)
        if err:
            send(chat_id, f"❌ {err}")
            return
    from maskai.utils.html import escape_html
    cat_name = p["cat"]
    result = supabase_get("maskai_categories", {"name": f"ilike.{cat_name}", "type": f"eq.{p['type']}", "select": "id", "limit": "1"})
    cats = result.data if result.ok and isinstance(result.data, list) else []
    cat_id = cats[0]["id"] if cats else get_fallback_category(user_id, p["type"])
    if not cat_id:
        send(chat_id, "❌ Kategori tidak ditemukan.")
        return
    from maskai.repositories.transaction_repository import create_transaction, CreateTransactionStatus
    result = create_transaction(
        user_id=user_id,
        update_id=p.get("update_id"),
        payload={
            "user_id": user_id, "type": p["type"], "amount": f"{amount:.2f}",
            "category_id": cat_id, "description": p["desc"], "transaction_dt": tgl, "currency": "IDR",
        },
        source="natural",
    )
    if result.status == CreateTransactionStatus.FAILED:
        send(chat_id, "❌ Gagal menyimpan.")
        return
    if result.status == CreateTransactionStatus.ALREADY_EXISTS:
        send(chat_id, "✅ Transaksi ini sudah pernah diproses sebelumnya.")
        return
    send(chat_id, f"✅ Tersimpan!\n{p['desc']}\n💰 Rp {amount:,.0f}\n📅 {tgl}", parse_mode="HTML")

# ── Main Polling Loop ──
def main():
    log.info("MASKAI Bot v2 starting...")
    offset_store = OffsetStore(config.OFFSET_FILE)
    offset = offset_store.load()
    
    err_count = 0
    while True:
        try:
            r = requests.get(f"{TELEGRAM_API}/getUpdates",
                params={"offset": offset, "timeout": 30}, timeout=config.POLL_TIMEOUT)
            if r.status_code < 200 or r.status_code >= 300:
                err_count += 1
                log.warning(f"getUpdates {r.status_code} ({err_count}/5)")
                if err_count >= 5:
                    log.critical("Too many errors, stopping")
                    break
                time_module.sleep(config.HTTP_TIMEOUT_SHORT)
                continue
            err_count = 0
            data = r.json()
            if not data.get("ok"):
                continue
            for upd in data.get("result", []):
                next_offset = upd["update_id"] + 1
                try:
                    msg = upd.get("message") or upd.get("edited_message")
                    cb = upd.get("callback_query")
                    if cb:
                        cb_user_id = cb.get("from", {}).get("id", 0)
                        if is_authorized(cb_user_id):
                            data_cb = cb.get("data", "")
                            chat_id = cb.get("message", {}).get("chat", {}).get("id")
                            if data_cb == "menu_kategori":
                                cmd_kategori(chat_id, cb_user_id)
                            elif data_cb.startswith("kategori_"):
                                cat_id = data_cb.split("_")[1]
                                cat = get_accessible_category(cat_id, cb_user_id)
                                if cat:
                                    label = "Pemasukan 💰" if cat["type"] == "I" else "Pengeluaran 💳"
                                    keyboard = {"inline_keyboard": []}
                                    if cat.get("user_id") != 0:
                                        keyboard["inline_keyboard"].append([{"text": "🗑 Hapus", "callback_data": f"katdelok_{cat_id}"}])
                                    send(chat_id, f"📋 <b>{escape_html(cat.get('icon','📦'))} {escape_html(cat['name'])}</b>\nTipe: {escape_html(label)}\n\n<code>/editkat {escape_html(cat_id)} &lt;nama baru&gt;</code>", parse_mode="HTML", reply_markup=keyboard)
                                else:
                                    send(chat_id, "❌ Kategori tidak ditemukan.")
                            elif data_cb.startswith("katdelok_"):
                                cat_id = data_cb.split("_")[1]
                                ok, err = delete_owned_category(cat_id, cb_user_id)
                                send(chat_id, "✅ Dihapus." if ok else f"❌ {err}")
                    elif msg:
                        result = process(msg, upd["update_id"])
                        if result == "__STOP__":
                            log.info("Stop signal received")
                            offset = next_offset
                            offset_store.save(offset)
                            return
                    # Advance offset after successful processing
                    offset = next_offset
                    offset_store.save(offset)
                except Exception as exc:
                    log.exception("Unhandled update error update_id=%s", upd["update_id"])
                    # Don't advance offset — retry on next poll
        except requests.RequestException as exc:
            err_count += 1
            log.error("Polling request error (%s/5): %s", err_count, exc)
            if err_count >= 5:
                log.critical("Polling failed %s times, stopping", err_count)
                break
            time_module.sleep(config.HTTP_TIMEOUT_SHORT)
        except (ValueError, OSError) as exc:
            err_count += 1
            log.error("Loop error (%s/5): %s", err_count, exc)
            if err_count >= 5:
                break
            time_module.sleep(config.HTTP_TIMEOUT_SHORT)
        offset_store.save(offset)

if __name__ == "__main__":
    main()
