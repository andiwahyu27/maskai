#!/usr/bin/env python3
"""MASKAI Bot v2 - Stable Telegram Finance Tracker"""
import os, sys, json, logging, time, re, requests
from datetime import datetime, timedelta

# ── Config ──
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pgnzzukciwtcxyzjuxlc.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DAHONO_KEY = os.environ.get("DAHONO_KEY", "")
DAHONO_URL = "https://gateway.dahono.com/v1"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OFFSET_FILE = os.environ.get("MASKAI_OFFSET_FILE", "/var/lib/maskai-bot/offset.txt")
try:
    os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
except PermissionError:
    OFFSET_FILE = "/tmp/maskai_offset.txt"
SUPABASE_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("maskai")
BOT_START_TIME = time.time()
ADMIN_IDS = [1367356347]
pending = {}  # pending date responses

from zoneinfo import ZoneInfo
TZ = ZoneInfo(os.environ.get("TZ", "Asia/Jakarta"))

def is_authorized(user_id):
    return user_id in ADMIN_IDS

def log_security(action, user_id, detail=""):
    log.warning(f"SECURITY | {action} | user={user_id} | {detail}")

def parse_positive_amount(value):
    """Validate and parse amount. Returns (amount, None) or (None, error_msg)"""
    try:
        amt = float(value)
    except (ValueError, TypeError):
        return None, "Jumlah tidak valid"
    if amt <= 0:
        return None, "Jumlah harus lebih dari 0"
    if amt > 999999999.99:
        return None, "Jumlah terlalu besar"
    return amt, None

def escape_md(text):
    """Escape special characters for Telegram MarkdownV2"""
    chars = "_*[]()~`>#+-=|{}.!\\"
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text

# ── API Helpers ──
class ApiResult:
    """Typed API result"""
    def __init__(self, ok, data=None, status=None, error=None):
        self.ok = ok
        self.data = data
        self.status = status
        self.error = error

def api_get(url, **kw):
    """Safe GET with typed result"""
    try:
        r = requests.get(url, timeout=kw.pop("timeout", 15), **kw)
        if r.status_code != 200:
            log.warning(f"API GET {r.status_code}: {r.text[:100]}")
            return ApiResult(False, status=r.status_code, error=r.text[:200])
        return ApiResult(True, data=r.json() if r.text else {}, status=200)
    except requests.Timeout:
        log.error(f"API GET timeout: {url[:80]}")
        return ApiResult(False, error="timeout")
    except requests.ConnectionError:
        log.error(f"API GET connection: {url[:80]}")
        return ApiResult(False, error="connection")
    except ValueError as e:
        log.error(f"API GET invalid JSON: {e}")
        return ApiResult(False, error="invalid_json")
    except Exception as e:
        log.error(f"API GET error: {e}")
        return ApiResult(False, error=str(e)[:200])

def api_post(url, json=None, data=None, **kw):
    """Safe POST with typed result"""
    try:
        r = requests.post(url, json=json, data=data, timeout=kw.pop("timeout", 15), **kw)
        if r.status_code not in (200, 201):
            log.warning(f"API POST {r.status_code}: {r.text[:100]}")
            return ApiResult(False, status=r.status_code, error=r.text[:200])
        return ApiResult(True, data=r.json() if r.text else {}, status=r.status_code)
    except requests.Timeout:
        log.error(f"API POST timeout: {url[:80]}")
        return ApiResult(False, error="timeout")
    except requests.ConnectionError:
        log.error(f"API POST connection: {url[:80]}")
        return ApiResult(False, error="connection")
    except ValueError as e:
        log.error(f"API POST invalid JSON: {e}")
        return ApiResult(False, error="invalid_json")
    except Exception as e:
        log.error(f"API POST error: {e}")
        return ApiResult(False, error=str(e)[:200])

def tg(method, data=None):
    """Telegram API call"""
    url = f"{TELEGRAM_API}/{method}"
    if data:
        result = api_post(url, json=data)
    else:
        result = api_get(url)
    return result.data if result.ok else {"ok": False, "error": result.error}

def send(chat_id, text, parse_mode=None, reply_markup=None):
    """Send Telegram message"""
    d = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode: d["parse_mode"] = parse_mode
    if reply_markup: d["reply_markup"] = reply_markup
    return tg("sendMessage", d)

def claude(messages, max_tokens=500):
    """Claude via Dahono"""
    r = requests.post(f"{DAHONO_URL}/chat/completions",
        json={"model": "dahono/claude-sonnet-4.5-free", "messages": messages, "max_tokens": max_tokens},
        headers={"Authorization": f"Bearer {DAHONO_KEY}", "Content-Type": "application/json"}, timeout=30)
    if r.status_code == 200 and r.text:
        return r.json()["choices"][0]["message"]["content"]
    return None

def supabase_get(table, params=None):
    """Supabase GET. params: dict or list of (k,v) tuples for duplicate keys"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        if isinstance(params, dict):
            q = "&".join(f"{k}={v}" for k, v in params.items())
        else:
            q = "&".join(f"{k}={v}" for k, v in params)
        url += f"?{q}"
    result = api_get(url, headers=SUPABASE_HEADERS)
    return result.data if result.ok else []

def supabase_post(table, data):
    """Supabase POST"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    result = api_post(url, json=data, headers=SUPABASE_HEADERS)
    return result.data if result.ok else {}

def supabase_delete(table, field, value):
    """Supabase DELETE"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{field}=eq.{value}"
    r = requests.delete(url, headers=SUPABASE_HEADERS, timeout=10)
    return r.status_code in (200, 204)

def api_patch(url, json=None, **kw):
    """Safe PATCH with typed result"""
    try:
        r = requests.patch(url, json=json, timeout=kw.pop("timeout", 15), **kw)
        if r.status_code not in (200, 201, 204):
            log.warning(f"API PATCH {r.status_code}: {r.text[:100]}")
            return ApiResult(False, status=r.status_code, error=r.text[:200])
        return ApiResult(True, data=r.json() if r.text else {}, status=r.status_code)
    except requests.Timeout:
        return ApiResult(False, error="timeout")
    except requests.ConnectionError:
        return ApiResult(False, error="connection")
    except ValueError:
        return ApiResult(False, error="invalid_json")
    except requests.RequestException as e:
        return ApiResult(False, error=str(e)[:200])

def api_delete(url, **kw):
    """Safe DELETE with typed result"""
    try:
        r = requests.delete(url, timeout=kw.pop("timeout", 15), **kw)
        if r.status_code not in (200, 204):
            log.warning(f"API DELETE {r.status_code}: {r.text[:100]}")
            return ApiResult(False, status=r.status_code, error=r.text[:200])
        return ApiResult(True, data={}, status=r.status_code)
    except requests.Timeout:
        return ApiResult(False, error="timeout")
    except requests.ConnectionError:
        return ApiResult(False, error="connection")
    except requests.RequestException as e:
        return ApiResult(False, error=str(e)[:200])

def supabase_patch(table, filters, data):
    """Supabase PATCH — uses requests.patch with dual filter"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if filters:
        q = "&".join(f"{k}=eq.{v}" for k, v in filters)
        url += f"?{q}"
    result = api_patch(url, json=data, headers=SUPABASE_HEADERS)
    return result.data if result.ok else None

# ── Category Ownership Helpers ──
def get_accessible_category(cat_id, user_id):
    """Get category if user can access it (global or owned)"""
    cats = supabase_get("maskai_categories", {"id": f"eq.{cat_id}", "select": "id,name,icon,type,user_id"})
    if not cats:
        return None
    cat = cats[0]
    if cat.get("user_id") not in (0, user_id):
        return None
    return cat

def is_category_owner(cat, user_id):
    """Check if user owns this category (not global, not other user)"""
    return cat and cat.get("user_id") == user_id

def list_accessible_categories(user_id):
    """List categories visible to user: own + global"""
    # Use two queries — Supabase doesn't support OR
    own = supabase_get("maskai_categories", {"user_id": f"eq.{user_id}", "select": "id,name,icon,type,user_id"})
    global_cats = supabase_get("maskai_categories", {"user_id": "eq.0", "select": "id,name,icon,type,user_id"})
    return (own or []) + (global_cats or [])

def delete_owned_category(cat_id, user_id):
    """Delete category if user owns it. Uses id+user_id filter"""
    cat = get_accessible_category(cat_id, user_id)
    if not cat:
        return False, "Kategori tidak ditemukan"
    if cat.get("user_id") == 0:
        return False, "Kategori global tidak bisa dihapus"
    # Delete with dual filter — extra safety
    r = api_delete(f"{SUPABASE_URL}/rest/v1/maskai_categories?id=eq.{cat_id}&user_id=eq.{user_id}", headers=SUPABASE_HEADERS)
    if not r.ok:
        return False, "Gagal menghapus"
    return True, None

def update_owned_category(cat_id, user_id, payload):
    """Update category if user owns it. Uses id+user_id filter"""
    cat = get_accessible_category(cat_id, user_id)
    if not cat:
        return False, "Kategori tidak ditemukan"
    if cat.get("user_id") == 0:
        return False, "Kategori global tidak bisa diedit"
    result = supabase_patch("maskai_categories", [("id", cat_id), ("user_id", user_id)], payload)
    if not result:
        return False, "Gagal update"
    return True, None

# ── Commands ──

def cmd_start(chat_id):
    msg = """🤖 *MASKAI Bot v2*

💰 *Input Natural* — ketik bebas:
• `beli telur 20rb di toko` → pengeluaran
• `gaji 5 juta` → pemasukan
• `jajan bakso 15rb` → pengeluaran
• `pemasukan 1jt dari honor`

📊 *Laporan*:
• `/laporan` — 5 transaksi terakhir
• `/laporan hari ini`
• `/laporan minggu ini`
• `/laporan bulan ini`
• `/laporan 2026-07-20 2026-07-28`

📋 *Kategori*:
• `/kategori` — lihat semua
• `/editkat <id> <nama baru>` — edit
• `/hapuskat <id>` — hapus
• `/tambahkat <I/E> <nama> [icon]` — tambah

💰 `/saldo` — cek saldo
📝 `/hutang <nama> <jumlah>` `/piutang <nama> <jumlah>`
🛒 `/keranjang <jumlah> <desk>`
📌 `/status` — cek bot"""
    send(chat_id, msg, parse_mode="MarkdownV2")

def cmd_laporan(chat_id, user_id, text):
    """Handle /laporan"""
    parts = text.strip().split()
    now = datetime.now(TZ)

    if len(parts) == 3:  # date range
        try:
            d1, d2 = parts[1], parts[2]
            since, until = f"{d1}T00:00:00", f"{d2}T23:59:59"
            txs = supabase_get("maskai_transactions", [
                ("user_id", f"eq.{user_id}"),
                ("transaction_dt", f"gte.{since}"),
                ("transaction_dt", f"lte.{until}"),
                ("select", "type,amount,description,transaction_dt,category_id"),
                ("order", "transaction_dt.desc")
            ])
            periode = f"{d1} s/d {d2}"
        except (ValueError, IndexError):
            send(chat_id, "❌ Format: /laporan 2026-07-20 2026-07-28")
            return
    elif len(parts) == 1:  # last 5
        txs = supabase_get("maskai_transactions", {
            "user_id": f"eq.{user_id}", "select": "type,amount,description,transaction_dt,category_id",
            "order": "transaction_dt.desc", "limit": "5"
        })
        periode = "Terbaru"
    else:
        cmd = text.lower()
        if "hari ini" in cmd:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            periode = "Hari Ini"
        elif "minggu" in cmd:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
            periode = "Minggu Ini"
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            periode = "Bulan Ini"
        since = start.isoformat()
        txs = supabase_get("maskai_transactions", {
            "user_id": f"eq.{user_id}", "transaction_dt": f"gte.{since}",
            "select": "type,amount,description,transaction_dt,category_id",
            "order": "transaction_dt.desc"
        })

    if not txs:
        send(chat_id, f"📊 *Laporan {periode}*\n\nBelum ada transaksi.", parse_mode="MarkdownV2")
        return

    cats = {c["id"]: c["name"] for c in supabase_get("maskai_categories", {"select": "id,name"})}

    income = sum(t["amount"] for t in txs if t["type"] == "I")
    expense = sum(t["amount"] for t in txs if t["type"] == "E")
    selisih = income - expense

    msg = f"📊 *Laporan {periode}*\n\n"
    msg += "💰 *Ringkasan:*\n"
    msg += f"📥 Pemasukan: Rp {income:,.0f}\n"
    msg += f"📤 Pengeluaran: Rp {expense:,.0f}\n"
    msg += f"📊 Selisih: Rp {selisih:,.0f}\n"
    msg += f"🛒 {len(txs)} transaksi\n\n"
    msg += "📋 *Transaksi Terbaru:*\n"

    for t in txs[:5]:
        dt = datetime.strptime(t["transaction_dt"][:10], "%Y-%m-%d")
        cat = cats.get(t.get("category_id"), "Lainnya")
        label = "Pemasukan" if t["type"] == "I" else "Pengeluaran"
        msg += f"\n📅 {dt.strftime('%d %b %Y')}\n📝 {cat} ({label})\n💵 Rp {t['amount']:,.0f}\n"

    send(chat_id, msg, parse_mode="MarkdownV2")

def cmd_saldo(chat_id, user_id):
    bal = supabase_get("maskai_balance", {"user_id": f"eq.{user_id}", "select": "balance"})
    amount = bal[0]["balance"] if bal else 0
    send(chat_id, f"💰 *Saldo*\nRp {amount:,.0f}", parse_mode="MarkdownV2")

def cmd_debt(chat_id, user_id, text):
    parts = text.strip().split()
    cmd = parts[0].lower()
    is_hutang = cmd == "/hutang"
    rest = text[8:] if is_hutang else text[9:]
    args = rest.strip().split()
    if len(args) < 2 or not args[1].replace(".","").isdigit():
        send(chat_id, f"Format: {cmd} <nama> <jumlah> <desk>")
        return
    data = {"user_id": user_id, "direction": "O" if is_hutang else "T",
            "counterparty": args[0], "amount": float(args[1]),
            "description": " ".join(args[2:]) or "-", "status": "open", "currency": "IDR"}
    result = supabase_post("maskai_debts", data)
    if not result:
        send(chat_id, "❌ Gagal menyimpan.")
        return
    label = "Hutang" if is_hutang else "Piutang"
    send(chat_id, f"📝 *{label}*\nRp {float(args[1]):,.0f}\n👤 {args[0]}", parse_mode="MarkdownV2")

def cmd_keranjang(chat_id, user_id, text):
    rest = text[11:].strip()
    args = rest.split()
    if not args or not args[0].replace(".","").isdigit():
        send(chat_id, "Format: /keranjang <jumlah> <desk>")
        return
    result = supabase_post("maskai_keranjang", {"user_id": user_id, "amount": float(args[0]),
        "description": " ".join(args[1:]) or "-"})
    if result:
        send(chat_id, f"🛒 *Keranjang*\nRp {float(args[0]):,.0f}\n_Status: Belum teralisasi_", parse_mode="MarkdownV2")
    else:
        send(chat_id, "❌ Gagal menyimpan ke keranjang.")

def cmd_kategori(chat_id, user_id):
    """List categories accessible to user"""
    cats = list_accessible_categories(user_id)
    if not cats:
        send(chat_id, "Belum ada kategori.")
        return
    msg = "📋 *Kategori*\n"
    for c in cats:
        icon = c.get("icon", "📦")
        tipe = "💰" if c["type"] == "I" else "💳"
        global_tag = " 🌐" if c.get("user_id") == 0 else ""
        msg += f"\n#{c['id']} {icon} {c['name']} {tipe}{global_tag}"
    msg += "\n\n/editkat <id> <nama>\n/hapuskat <id>\n/tambahkat <I/E> <nama>"
    send(chat_id, msg, parse_mode="MarkdownV2")

def cmd_editkat(chat_id, user_id, text):
    """Edit category with ownership check"""
    parts = text.strip().split()
    if len(parts) < 3:
        send(chat_id, "Format: /editkat <id> <nama baru>")
        return
    cat_id = parts[1]
    new_name = " ".join(parts[2:])
    ok, err = update_owned_category(cat_id, user_id, {"name": new_name})
    if ok:
        send(chat_id, f"✅ Kategori #{cat_id} diubah jadi *{escape_md(new_name)}*", parse_mode="MarkdownV2")
    else:
        send(chat_id, f"❌ {err}")

def cmd_hapuskat(chat_id, user_id, text):
    """Delete category with ownership check"""
    parts = text.strip().split()
    if len(parts) < 2:
        send(chat_id, "Format: /hapuskat <id>")
        return
    cat_id = parts[1]
    ok, err = delete_owned_category(cat_id, user_id)
    if ok:
        send(chat_id, f"✅ Kategori #{cat_id} dihapus.")
    else:
        send(chat_id, f"❌ {err}")

def cmd_tambahkat(chat_id, user_id, text):
    """Add category with user ownership, multi-word name support"""
    parts = text.strip().split()
    if len(parts) < 3:
        send(chat_id, "Format: /tambahkat <I/E> <nama> [icon]")
        return
    tx_type = parts[1].upper()
    if tx_type not in ("I", "E"):
        send(chat_id, "Tipe harus I (Pemasukan) atau E (Pengeluaran)")
        return
    # Multi-word name: join all words, detect trailing emoji
    name_parts = parts[2:]
    icon = "📦"
    if len(name_parts[-1]) == 1 and len(name_parts) > 1:
        icon = name_parts.pop()
    name = " ".join(name_parts)
    if not name:
        send(chat_id, "❌ Nama kategori tidak boleh kosong.")
        return
    data = {"name": name, "type": tx_type, "icon": icon, "user_id": user_id}
    result = supabase_post("maskai_categories", data)
    if result:
        send(chat_id, f"✅ Kategori *{escape_md(name)}* ({'Pemasukan' if tx_type=='I' else 'Pengeluaran'}) ditambahkan.", parse_mode="MarkdownV2")
    else:
        send(chat_id, "❌ Gagal menambah kategori.")

def cmd_menu(chat_id):
    """Simple menu without inline keyboard"""
    keyboard = {"keyboard": [
        ["/laporan", "/saldo"],
        ["/kategori", "/keranjang"],
        ["/status", "/help"]
    ], "resize_keyboard": True}
    send(chat_id, "🤖 *MASKAI Menu*\nPilih dari keyboard atau ketik perintah:", parse_mode="MarkdownV2", reply_markup=keyboard)

def cmd_ocr(chat_id, user_id, file_id):
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

    r = requests.post(f"{DAHONO_URL}/chat/completions", json=payload,
        headers={"Authorization": f"Bearer {DAHONO_KEY}", "Content-Type": "application/json"}, timeout=30)

    if r.status_code != 200 or not r.text:
        log.error(f"OCR error {r.status_code}: {r.text[:200] if r.text else 'empty'}")
        send(chat_id, "❌ Gagal membaca struk.")
        return

    content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    if not content:
        send(chat_id, "❌ Struk tidak dapat dibaca.")
        return

    try:
        data = json.loads(re.sub(r"```json|```", "", content).strip())
    except (json.JSONDecodeError, ValueError):
        log.error(f"OCR parse: {content[:200]}")
        send(chat_id, "❌ Struk tidak dapat dibaca.")
        return

    if data.get("error"):
        send(chat_id, "❌ Struk tidak jelas. Coba foto ulang.")
        return

    # Validate OCR amount using Decimal
    from decimal import Decimal, InvalidOperation
    try:
        total = Decimal(str(data.get("total", 0)))
        if total <= 0:
            send(chat_id, "❌ Jumlah di struk tidak valid.")
            return
        if total > 999999999.99:
            send(chat_id, "❌ Jumlah terlalu besar.")
            return
    except (InvalidOperation, ValueError):
        send(chat_id, "❌ Jumlah di struk tidak valid.")
        return

    fallback_cat = get_fallback_category(user_id, "E")
    if not fallback_cat:
        send(chat_id, "❌ Gagal menyimpan — kategori default tidak ditemukan.")
        return

    result = supabase_post("maskai_transactions", {
        "user_id": user_id, "type": "E", "amount": float(total),
        "category_id": fallback_cat, "description": f"{data.get('items','-')} ({data.get('toko','Struk')})",
        "transaction_dt": data.get("tanggal", datetime.now(TZ).strftime("%Y-%m-%d")), "currency": "IDR"
    })
    if result:
        send(chat_id, f"🛒 *{escape_md(data.get('toko','Struk'))}*\n💰 Rp {data.get('total',0):,.0f}\n📋 {escape_md(data.get('items','-'))}\n📅 {data.get('tanggal','-')}\n\n✅ Auto disimpan!", parse_mode="MarkdownV2")
    else:
        send(chat_id, "❌ Gagal menyimpan transaksi.")

def cmd_natural(chat_id, user_id, text, update_id=None):
    """Parse natural language input"""
    send(chat_id, "⏳ Memproses...")
    prompt = f"""Parse text keuangan ini ke JSON.
Text: "{text}"

Return JSON: {{"jenis":"pemasukan" atau "pengeluaran","jumlah":<angka>,"kategori":"...","deskripsi":"...","tanggal":"YYYY-MM-DD" atau null}}

Aturan:
- "gaji","bonus","honor","pemasukan","hasil","pendapatan" → pemasukan
- Selain itu → pengeluaran
- "20rb" atau "20 ribu" → 20000, "1juta" → 1000000
- Jika ada tanggal spesifik (contoh: "kemarin", "28 juli", "minggu lalu"), isi field tanggal. Jika tidak ada, isi null."""

    result = claude([{"role": "user", "content": prompt}], 200)
    if not result:
        send(chat_id, "❌ Gagal memproses. Coba format jelas:\n• `beli telur 20rb`\n• `gaji 5 juta 28 juli`")
        return

    try:
        data = json.loads(re.sub(r"```json|```", "", result).strip())
    except (json.JSONDecodeError, ValueError):
        send(chat_id, "❌ Gagal parse. Coba lagi.")
        return

    tx_type = "I" if data.get("jenis") == "pemasukan" else "E"
    amount = data.get("jumlah", 0)
    
    # Validate amount
    amt, err = parse_positive_amount(amount)
    if err:
        send(chat_id, f"❌ {err}")
        return
    cat_name = data.get("kategori", "Lainnya")
    desc = data.get("deskripsi", "-")
    tgl = data.get("tanggal")
    
    # If no date provided, ask user
    if not tgl:
        # Save pending tx
        pending[chat_id] = {"type": tx_type, "amount": amount, "cat": cat_name, "desc": desc, "user_id": user_id, "update_id": update_id}
        send(chat_id, f"📅 *Kapan tanggal transaksinya?*\nTulis: `28 juli` atau `kemarin` atau `hari ini`", parse_mode="MarkdownV2")
        return
    
    # Convert relative dates
    if tgl.lower() in ("hari ini", "today"):
        tgl = datetime.now().strftime("%Y-%m-%d")
    elif tgl.lower() in ("kemarin", "yesterday"):
        tgl = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Parse "28 juli" style
    if not tgl.startswith("20"):
        try:
            dt = datetime.strptime(tgl.replace("juli","July").replace("june","June"), "%d %B")
            tgl = dt.strftime(f"{datetime.now().year}-%m-%d")
        except (ValueError, IndexError):
            pass

    cats = supabase_get("maskai_categories", {"name": f"ilike.{cat_name}", "type": f"eq.{tx_type}", "select": "id", "limit": "1"})
    cat_id = cats[0]["id"] if cats else get_fallback_category(user_id, tx_type)
    if not cat_id:
        send(chat_id, "❌ Kategori tidak ditemukan.")
        return

    result = supabase_post("maskai_transactions", {
        "user_id": user_id, "type": tx_type, "amount": amt, "category_id": cat_id,
        "description": desc, "transaction_dt": tgl, "currency": "IDR",
        "metadata": {"telegram_update_id": str(update_id), "source": "natural"} if update_id else None
    })
    if not result:
        send(chat_id, "❌ Gagal menyimpan transaksi.")
        return

    label = "Pemasukan" if tx_type == "I" else "Pengeluaran"
    esc_desc = escape_md(desc)
    esc_cat = escape_md(cat_name)
    send(chat_id, f"✅ *{label}*\nRp {amt:,.0f}\n{esc_desc}\nKategori: {esc_cat}\n📅 {tgl}", parse_mode="MarkdownV2")

def get_fallback_category(user_id, tx_type):
    """Lookup fallback category by name and type, avoid hardcoded IDs"""
    name = "Lainnya (Pemasukan)" if tx_type == "I" else "Lainnya (Pengeluaran)"
    # Try user's category first, then global
    for uid in (user_id, 0):
        cats = supabase_get("maskai_categories", {"user_id": f"eq.{uid}", "name": f"ilike.{name}", "type": f"eq.{tx_type}", "select": "id", "limit": "1"})
        if cats:
            return cats[0]["id"]
    return None

def handle_pending_date(chat_id, text):
    """Process user's date reply for pending transaction"""
    if chat_id not in pending:
        return
    p = pending.pop(chat_id)
    
    # Convert "28 juli" or "hari ini" to YYYY-MM-DD
    tgl = text.strip().lower()
    if tgl in ("hari ini", "today", ""):
        tgl = datetime.now().strftime("%Y-%m-%d")
    elif tgl == "kemarin":
        tgl = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        # Try to parse
        try:
            dt = datetime.strptime(tgl.replace("juli","July").replace("juni","June").replace("agustus","August"), "%d %B")
            tgl = dt.strftime(f"{datetime.now().year}-%m-%d")
        except (ValueError, IndexError):
            tgl = datetime.now().strftime("%Y-%m-%d")  # fallback
    
    cats = supabase_get("maskai_categories", {"name": f"ilike.{p['cat']}", "type": f"eq.{p['type']}", "select": "id", "limit": "1"})
    cat_id = cats[0]["id"] if cats else get_fallback_category(p["user_id"], p["type"])
    if not cat_id:
        send(chat_id, "❌ Kategori tidak ditemukan.")
        return
    
    result = supabase_post("maskai_transactions", {
        "user_id": p["user_id"], "type": p["type"], "amount": p["amount"], "category_id": cat_id,
        "description": p["desc"], "transaction_dt": tgl, "currency": "IDR",
        "metadata": {"telegram_update_id": str(p.get("update_id")), "source": "natural"} if p.get("update_id") else None
    })
    if not result:
        send(chat_id, "❌ Gagal menyimpan transaksi.")
        return
    
    label = "Pemasukan" if p["type"] == "I" else "Pengeluaran"
    send(chat_id, f"✅ *{label}*\nRp {p['amount']:,.0f}\n{escape_md(p['desc'])}\nKategori: {escape_md(p['cat'])}\n📅 {tgl}", parse_mode="MarkdownV2")

def cmd_usage(chat_id):
    """Show Supabase usage stats"""
    send(chat_id, "⏳ Cek usage Supabase...")
    tables = {
        "maskai_transactions": "Transaksi",
        "maskai_debts": "Hutang/Piutang",
        "maskai_keranjang": "Keranjang",
        "maskai_categories": "Kategori",
        "maskai_balance": "Saldo"
    }
    total_rows = 0
    msg = "📊 *Supabase Usage*\n\n"
    for t, label in tables.items():
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{t}?select=count",
            headers={**SUPABASE_HEADERS, "Prefer": "count=exact"}, timeout=5)
        ct = r.headers.get("content-range", "").split("/")[-1] if "content-range" in r.headers else "?"
        total_rows += int(ct) if ct.isdigit() else 0
        msg += f"  {label}: {ct}\n"
    est_size_mb = (total_rows * 0.5) / 1024
    msg += f"\n📦 *Estimasi:*\n  Total rows: {total_rows}\n  Est. size: {est_size_mb:.1f} MB"
    send(chat_id, msg, parse_mode="MarkdownV2")

# ── Command Router ──

def process(msg, update_id=None):
    chat_id = msg.get("chat", {}).get("id")
    user_id = msg.get("from", {}).get("id", 0)
    text = (msg.get("text", "") or msg.get("caption", "")).strip()
    photo = msg.get("photo")

    if not chat_id: return

    if not is_authorized(user_id):
        log_security("unauthorized", user_id, f"text={text[:50]}")
        send(chat_id, "❌ Akses tidak diizinkan.")
        return

    if photo:
        cmd_ocr(chat_id, user_id, photo[-1]["file_id"])
        return

    if not text: return

    # Check if user has a pending date response
    if chat_id in pending:
        handle_pending_date(chat_id, text.strip())
        return

    cmd = text.split()[0].lower() if text else ""
    args = text

    # Command routing
    if cmd in ("/start", "/help"):
        cmd_start(chat_id)
    elif cmd in ("/menu", "/m"):
        cmd_menu(chat_id)
    elif cmd == "/saldo":
        cmd_saldo(chat_id, user_id)
    elif cmd in ("/hutang", "/piutang"):
        cmd_debt(chat_id, user_id, args)
    elif cmd == "/keranjang":
        cmd_keranjang(chat_id, user_id, args)
    elif cmd == "/kategori":
        cmd_kategori(chat_id, user_id)
    elif cmd == "/editkat":
        cmd_editkat(chat_id, user_id, args)
    elif cmd == "/hapuskat":
        cmd_hapuskat(chat_id, user_id, args)
    elif cmd == "/tambahkat":
        cmd_tambahkat(chat_id, user_id, text)
    elif cmd in ("/laporan", "/report", "/r"):
        cmd_laporan(chat_id, user_id, args)
    elif cmd == "/status":
        uptime = time.strftime("%Hh %Mm", time.gmtime(time.time() - BOT_START_TIME))
        # Count DB rows
        db = {}
        for t in ["maskai_transactions","maskai_debts","maskai_keranjang","maskai_categories"]:
            r = requests.get(f"{SUPABASE_URL}/rest/v1/{t}?select=count", headers={**SUPABASE_HEADERS, "Prefer": "count=exact"}, timeout=5)
            db[t] = r.headers.get("content-range", "").split("/")[-1] if "content-range" in r.headers else "?"
        send(chat_id, f"📌 *MASKAI Bot v2*\n✅ Aktif\n⏱ {uptime}\n🧠 Teks: Claude Sonnet 4.5\n🖼 OCR: GPT-5.5\n\n💾 *Database:*\n TX: {db.get('maskai_transactions','?')} | Hutang: {db.get('maskai_debts','?')}\n Keranjang: {db.get('maskai_keranjang','?')} | Kat: {db.get('maskai_categories','?')}", parse_mode="MarkdownV2")
    elif cmd in ("/usage", "/cekdb"):
        cmd_usage(chat_id)
    elif cmd == "/sync":
        try:
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials
            
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("/home/ubuntu/maskai/service-account.json", scope)
            client = gspread.authorize(creds)
            
            sheet_id = "1dBkYHEGsftjqH2NA9bd5EJ58Cc_HYKt8rVoWk0RdQUg"
            sheet = client.open_by_key(sheet_id).sheet1
            
            # Fetch all transactions
            txs = supabase_get("maskai_transactions", {
                "select": "id,type,amount,description,transaction_dt,created_at,category_id",
                "order": "id.asc"
            })
            cats = {c["id"]: c["name"] for c in supabase_get("maskai_categories", {"select": "id,name"})}
            
            if not txs:
                send(chat_id, "❌ Tidak ada transaksi.")
                return
            
            # Clear and rewrite
            sheet.clear()
            sheet.append_row(["ID", "Jenis", "Jumlah", "Kategori", "Deskripsi", "TANGGAL TRANSAKSI", "TANGGAL INPUT", "WAKTU INPUT"])
            
            rows = []
            for t in txs:
                created = t.get("created_at", "")
                if created:
                    # Convert UTC to WIB (UTC+7)
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        wib = dt + timedelta(hours=7)
                        tgl_input = wib.strftime("%Y-%m-%d")
                        waktu_input = wib.strftime("%H:%M:%S")
                    except (ValueError, IndexError):
                        tgl_input = created[:10] if len(created) >= 10 else "-"
                        waktu_input = created[11:19] if len(created) >= 19 else "-"
                else:
                    tgl_input = "-"
                    waktu_input = "-"
                rows.append([
                    str(t["id"]),
                    "Pemasukan" if t["type"] == "I" else "Pengeluaran",
                    t["amount"],
                    cats.get(t.get("category_id"), "-"),
                    t.get("description", "-"),
                    t["transaction_dt"][:10],
                    tgl_input,
                    waktu_input
                ])
            
            # Batch append (max 1000 per batch)
            for i in range(0, len(rows), 500):
                sheet.append_rows(rows[i:i+500])
            
            count = len(txs)
            send(chat_id, f"✅ Sudah dilakukan sinkronisasi ke Google Sheets.\n{count} transaksi berhasil disinkron.\nSilahkan cek spreadsheet", parse_mode="MarkdownV2")
            
        except Exception as e:
            log.error(f"Sync error: {e}")
            send(chat_id, f"❌ Gagal sync: {e}")
    elif cmd == "/resetdb":
        if user_id not in ADMIN_IDS:
            send(chat_id, "❌ Hanya admin yang bisa.")
            return
        # Delete all transactions, debts, keranjang
        for table in ["maskai_transactions", "maskai_debts", "maskai_keranjang"]:
            r = requests.delete(f"{SUPABASE_URL}/rest/v1/{table}?user_id=eq.{user_id}", headers=SUPABASE_HEADERS, timeout=10)
        send(chat_id, "✅ Database dikosongkan.\nSemua transaksi, hutang/piutang, dan keranjang dihapus.")
    elif cmd == "/stop":
        if user_id in ADMIN_IDS:
            send(chat_id, "🛑 Bot dihentikan.")
            # Signal main loop to stop gracefully
            return "__STOP__"
        else:
            send(chat_id, "❌ Tidak punya izin.")
    elif text:
        # Natural language input
        cmd_natural(chat_id, user_id, text, update_id)

# ── Main ──

def main():
    log.info("MASKAI Bot v2 starting...")
    # Safe offset read — handle empty/corrupt file
    offset = 0
    if os.path.exists(OFFSET_FILE):
        try:
            content = open(OFFSET_FILE).read().strip()
            if content:
                offset = int(content)
        except (ValueError, OSError) as e:
            log.warning(f"Corrupt offset file {OFFSET_FILE}: {e}, resetting to 0")
            offset = 0
    if "/tmp" in OFFSET_FILE:
        log.warning("Using /tmp fallback for offset — may be lost on reboot")
    err_count = 0

    while True:
        try:
            r = requests.get(f"{TELEGRAM_API}/getUpdates",
                params={"offset": offset, "timeout": 30}, timeout=35)
            if r.status_code != 200:
                err_count += 1
                log.warning(f"getUpdates {r.status_code} ({err_count}/5)")
                if err_count >= 5:
                    log.critical("Max errors, stopping.")
                    break
                time.sleep(5)
                continue

            data = r.json()
            if not data.get("ok"):
                err_count += 1
                log.warning(f"getUpdates failed ({err_count}/5): {data}")
                if err_count >= 5: break
                time.sleep(5)
                continue

            err_count = 0

            for upd in data.get("result", []):
                try:
                    msg = upd.get("message") or upd.get("edited_message")
                    cb = upd.get("callback_query")
                    if msg:
                        result = process(msg, upd["update_id"])
                        if result == "__STOP__":
                            log.info("Stop signal received, exiting...")
                            offset = upd["update_id"] + 1
                            with open(OFFSET_FILE + ".tmp", "w") as f:
                                f.write(str(offset))
                            os.rename(OFFSET_FILE + ".tmp", OFFSET_FILE)
                            return
                    elif cb:
                        # Auth check for callback
                        cb_user_id = cb.get("from", {}).get("id", 0)
                        if not is_authorized(cb_user_id):
                            log_security("unauthorized_callback", cb_user_id)
                            tg("answerCallbackQuery", {"callback_query_id": cb.get("id"), "text": "Akses tidak diizinkan"})
                            offset = upd["update_id"] + 1
                            continue
                        # Simple callback handler for inline buttons
                        chat_id = cb.get("message", {}).get("chat", {}).get("id")
                        data_cb = cb.get("data", "")
                        tg("answerCallbackQuery", {"callback_query_id": cb.get("id"), "text": ""})
                        # Route callbacks
                        if data_cb == "menu_kategori":
                            cmd_kategori(chat_id, cb_user_id)
                        elif data_cb.startswith("kategori_"):
                            # Show category detail — ownership-filtered
                            cat_id = data_cb.split("_")[1]
                            cat = get_accessible_category(cat_id, cb_user_id)
                            if not cat:
                                tg("answerCallbackQuery", {"callback_query_id": cb.get("id"), "text": "Kategori tidak ditemukan"})
                                continue
                            label = "Pemasukan" if cat["type"] == "I" else "Pengeluaran"
                            keyboard = {"inline_keyboard": []}
                            if is_category_owner(cat, cb_user_id):
                                keyboard["inline_keyboard"].append(
                                    [{"text": "🗑 Hapus", "callback_data": f"katdelok_{cat_id}"}]
                                )
                            keyboard["inline_keyboard"].append(
                                [{"text": "🔙 Kembali", "callback_data": "menu_kategori"}]
                            )
                            send(chat_id, f"📋 *{escape_md(cat.get('icon','📦'))} {escape_md(cat['name'])}*\nTipe: {label}\n\n/editkat {cat_id} <nama baru>", parse_mode="MarkdownV2", reply_markup=keyboard)
                        elif data_cb.startswith("katdelok_"):
                            cat_id = data_cb.split("_")[1]
                            ok, err = delete_owned_category(cat_id, cb_user_id)
                            if ok:
                                send(chat_id, f"✅ Kategori #{cat_id} dihapus.")
                                cmd_kategori(chat_id, cb_user_id)
                            else:
                                tg("answerCallbackQuery", {"callback_query_id": cb.get("id"), "text": err})
                                send(chat_id, f"❌ {err}")
                except Exception as e:
                    log.error(f"Update error: {e}")

                offset = upd["update_id"] + 1

            if data.get("result"):
                with open(OFFSET_FILE + ".tmp", "w") as f:
                    f.write(str(offset))
                os.rename(OFFSET_FILE + ".tmp", OFFSET_FILE)

        except (requests.Timeout, requests.ConnectionError, ValueError, OSError) as e:
            err_count += 1
            log.error(f"Loop error ({err_count}/5): {e}")
            if err_count >= 5: break
            time.sleep(5)

if __name__ == "__main__":
    main()
