"""MASKAI — All Telegram command handlers"""
import json, logging, re, time as time_module
from datetime import datetime, timedelta

from maskai.config import config, SUPABASE_URL, SUPABASE_KEY, BOT_TOKEN, DAHONO_KEY
from maskai.config import DAHONO_URL, TELEGRAM_API, SUPABASE_HEADERS, TZ
from maskai.utils.validation import parse_positive_amount
from maskai.utils.html import escape_html
from maskai.utils.dates import build_jakarta_date_range
from maskai.clients.telegram import send
from maskai.clients.supabase import supabase_get, supabase_post, supabase_patch, supabase_delete
from maskai.clients.dahono import claude
from maskai.repositories.category_repository import (
    get_accessible_category, list_accessible_categories,
    is_category_owner, delete_owned_category, update_owned_category
)
from maskai.state.pending_store import pending
from maskai.services.ocr_service import cmd_ocr

log = logging.getLogger("maskai.handlers.commands")

def cmd_start(chat_id):
    msg = """🤖 <b>MASKAI Bot v2</b>

💰 <b>Input Natural</b> — ketik bebas:
• <code>beli telur 20rb</code> → pengeluaran
• <code>gaji 5 juta</code> → pemasukan
• <code>jajan bakso 15rb</code> → pengeluaran
• <code>pemasukan 1jt dari honor</code>

📊 <b>Laporan</b>:
• <code>/laporan</code> — 5 transaksi terakhir
• <code>/laporan hari ini</code>
• <code>/laporan minggu ini</code>
• <code>/laporan bulan ini</code>
• <code>/laporan 2026-07-01 2026-07-31</code>

🛠 <b>Tools</b>:
• <code>/kategori</code> — lihat daftar kategori
• <code>/tambahkat &lt;I/E&gt; &lt;nama&gt; [icon]</code>
• <code>/editkat &lt;id&gt; &lt;nama baru&gt;</code>
• <code>/hapuskat &lt;id&gt;</code>
• <code>/saldo</code> — cek saldo
• <code>/hutang &lt;nama&gt; &lt;jumlah&gt;</code>
• <code>/piutang &lt;nama&gt; &lt;jumlah&gt;</code>
• <code>/keranjang &lt;jumlah&gt; &lt;desk&gt;</code>
• <code>/ocr</code> — reply foto struk
• <code>/menu</code> — daftar perintah
• <code>/status</code> — info bot
• <code>/sync</code> — sinkronisasi ke Google Sheets
• <code>/usage</code> — penggunaan database"""
    send(chat_id, msg, parse_mode="HTML")

def cmd_laporan(chat_id, user_id, text):
    """Handle /laporan"""
    parts = text.strip().split()
    now = datetime.now(TZ)

    if len(parts) == 3:  # date range
        try:
            d1, d2 = parts[1], parts[2]
            start_dt, end_dt = build_jakarta_date_range(d1, d2)
            since = start_dt.isoformat()
            until = end_dt.isoformat()
            tx_result = supabase_get("maskai_transactions", [
                ("user_id", f"eq.{user_id}"),
                ("transaction_dt", f"gte.{since}"),
                ("transaction_dt", f"lt.{until}"),
                ("select", "type,amount,description,transaction_dt,category_id"),
                ("order", "transaction_dt.desc")
            ])
            txs = tx_result.data if tx_result.ok and isinstance(tx_result.data, list) else []
            periode = f"{d1} s/d {d2}"
        except ValueError as e:
            msg = str(e)
            send(chat_id, f"❌ {msg}" if "Tanggal" in msg else "❌ Format: /laporan 2026-07-20 2026-07-28")
            return
        except IndexError:
            send(chat_id, "❌ Format: /laporan 2026-07-20 2026-07-28")
            return
    elif len(parts) == 1:  # last 5
        tx_result = supabase_get("maskai_transactions", {
            "user_id": f"eq.{user_id}", "select": "type,amount,description,transaction_dt,category_id",
            "order": "transaction_dt.desc", "limit": "5"
        })
        txs = tx_result.data if tx_result.ok and isinstance(tx_result.data, list) else []
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
        tx_result = supabase_get("maskai_transactions", {
            "user_id": f"eq.{user_id}", "transaction_dt": f"gte.{since}",
            "select": "type,amount,description,transaction_dt,category_id",
            "order": "transaction_dt.desc"
        })
        txs = tx_result.data if tx_result.ok and isinstance(tx_result.data, list) else []

    if not txs:
        send(chat_id, f"📊 <b>Laporan {escape_html(periode)}</b>\n\nBelum ada transaksi.", parse_mode="HTML")
        return

    cat_result = supabase_get("maskai_categories", {"select": "id,name"})
    cat_list = cat_result.data if cat_result.ok and isinstance(cat_result.data, list) else []
    cats = {c["id"]: c["name"] for c in cat_list}

    income = sum(t["amount"] for t in txs if t["type"] == "I")
    expense = sum(t["amount"] for t in txs if t["type"] == "E")
    selisih = income - expense

    msg = f"📊 <b>Laporan {escape_html(periode)}</b>\n\n"
    msg += "💰 <b>Ringkasan:</b>\n"
    msg += f"📥 Pemasukan: Rp {income:,.0f}\n"
    msg += f"📤 Pengeluaran: Rp {expense:,.0f}\n"
    msg += f"📊 Selisih: Rp {selisih:,.0f}\n"
    msg += f"🛒 {len(txs)} transaksi\n\n"
    msg += "📋 <b>Transaksi Terbaru:</b>\n"

    for t in txs[:5]:
        dt = datetime.strptime(t["transaction_dt"][:10], "%Y-%m-%d")
        cat = cats.get(t.get("category_id"), "Lainnya")
        label = "Pemasukan" if t["type"] == "I" else "Pengeluaran"
        msg += f"\n📅 {dt.strftime('%d %b %Y')}\n📝 {escape_html(cat)} ({escape_html(label)})\n💵 Rp {t['amount']:,.0f}\n"

    send(chat_id, msg, parse_mode="HTML")

def cmd_saldo(chat_id, user_id):
    result = supabase_get("maskai_balance", {"user_id": f"eq.{user_id}", "select": "balance"})
    bal = result.data if result.ok and isinstance(result.data, list) else []
    amount = bal[0]["balance"] if bal else 0
    send(chat_id, f"💰 <b>Saldo</b>\nRp {amount:,.0f}", parse_mode="HTML")

def cmd_debt(chat_id, user_id, text):
    parts = text.strip().split()
    cmd = parts[0].lower()
    is_hutang = cmd == "/hutang"
    rest = text[8:] if is_hutang else text[9:]
    args = rest.strip().split()
    if len(args) < 2 or not args[1].replace(".","").isdigit():
        send(chat_id, f"Format: {cmd} <nama> <jumlah> <desk>")
        return
    amount, err = parse_positive_amount(args[1])
    if err:
        send(chat_id, f"❌ {err}")
        return
    data = {"user_id": user_id, "direction": "O" if is_hutang else "T",
            "counterparty": args[0], "amount": format(amount, "f"),
            "description": " ".join(args[2:]) or "-", "status": "open", "currency": "IDR"}
    result = supabase_post("maskai_debts", data)
    if not result.ok:
        send(chat_id, "❌ Gagal menyimpan.")
        return
    label = "Hutang" if is_hutang else "Piutang"
    send(chat_id, f"📝 <b>{escape_html(label)}</b>\nRp {amount:,.0f}\n👤 {escape_html(args[0])}", parse_mode="HTML")

def cmd_keranjang(chat_id, user_id, text):
    rest = text[11:].strip()
    args = rest.split()
    if not args or not args[0].replace(".","").isdigit():
        send(chat_id, "Format: /keranjang <jumlah> <desk>")
        return
    price, err = parse_positive_amount(args[0])
    if err:
        send(chat_id, f"❌ {err}")
        return
    result = supabase_post("maskai_keranjang", {"user_id": user_id, "amount": format(price, "f"),
        "description": " ".join(args[1:]) or "-"})
    if result.ok:
        send(chat_id, f"🛒 <b>Keranjang</b>\nRp {price:,.0f}\n<i>Status: Belum teralisasi</i>", parse_mode="HTML")
    else:
        send(chat_id, "❌ Gagal menyimpan ke keranjang.")

def cmd_kategori(chat_id, user_id):
    """List categories accessible to user"""
    cats = list_accessible_categories(user_id)
    if not cats:
        send(chat_id, "Belum ada kategori.")
        return
    msg = "📋 <b>Kategori</b>\n"
    for c in cats:
        icon = c.get("icon", "📦")
        tipe = "💰" if c["type"] == "I" else "💳"
        global_tag = " 🌐" if c.get("user_id") == 0 else ""
        msg += f"\n#{escape_html(str(c['id']))} {escape_html(icon)} {escape_html(c['name'])} {tipe}{global_tag}"
    msg += "\n\n<code>/editkat &lt;id&gt; &lt;nama&gt;</code>\n<code>/hapuskat &lt;id&gt;</code>\n<code>/tambahkat &lt;I/E&gt; &lt;nama&gt;</code>"
    send(chat_id, msg, parse_mode="HTML")

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
        send(chat_id, f"✅ Kategori #{escape_html(cat_id)} diubah jadi <b>{escape_html(new_name)}</b>", parse_mode="HTML")
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
    if result.ok:
        send(chat_id, f"✅ Kategori <b>{escape_html(name)}</b> ({'Pemasukan' if tx_type=='I' else 'Pengeluaran'}) ditambahkan.", parse_mode="HTML")
    else:
        send(chat_id, "❌ Gagal menambah kategori.")

def cmd_menu(chat_id):
    """Simple menu without inline keyboard"""
    keyboard = {"keyboard": [
        ["/laporan", "/saldo"],
        ["/kategori", "/keranjang"],
        ["/status", "/help"]
    ], "resize_keyboard": True}
    send(chat_id, "🤖 <b>MASKAI Menu</b>\nPilih dari keyboard atau ketik perintah:", parse_mode="HTML", reply_markup=keyboard)

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
        send(chat_id, "❌ Gagal memproses. Coba format jelas:\n• <code>beli telur 20rb</code>\n• <code>gaji 5 juta 28 juli</code>", parse_mode="HTML")
        return

    try:
        data = json.loads(re.sub(r"```json|```", "", result).strip())
    except (json.JSONDecodeError, ValueError):
        send(chat_id, "❌ Gagal parse. Coba lagi.")
        return

    # Validate transaction type — reject invalid, don't default to expense
    jenis = str(data.get("jenis", "")).strip().lower()
    type_map = {"pemasukan": "I", "income": "I", "masuk": "I",
                "pengeluaran": "E", "expense": "E", "keluar": "E"}
    tx_type = type_map.get(jenis)
    if tx_type is None:
        send(chat_id, "❌ Jenis transaksi harus pemasukan atau pengeluaran.")
        return
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
        pending.set(chat_id, user_id, {"type": tx_type, "amount": amt, "cat": cat_name, "desc": desc, "user_id": user_id, "update_id": update_id})
        send(chat_id, f"📅 <b>Kapan tanggal transaksinya?</b>\nTulis: <code>28 juli</code> atau <code>kemarin</code> atau <code>hari ini</code>", parse_mode="HTML")
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

    result = supabase_get("maskai_categories", {"name": f"ilike.{cat_name}", "type": f"eq.{tx_type}", "select": "id", "limit": "1"})
    cats = result.data if result.ok and isinstance(result.data, list) else []
    cat_id = cats[0]["id"] if cats else get_fallback_category(user_id, tx_type)
    if not cat_id:
        send(chat_id, "❌ Kategori tidak ditemukan.")
        return

    result = supabase_post("maskai_transactions", {
        "user_id": user_id, "type": tx_type, "amount": format(amt, "f"), "category_id": cat_id,
        "description": desc, "transaction_dt": tgl, "currency": "IDR",
        "metadata": {"telegram_update_id": str(update_id), "source": "natural"} if update_id else None
    })
    if not result.ok:
        send(chat_id, "❌ Gagal menyimpan transaksi.")
        return

    label = "Pemasukan" if tx_type == "I" else "Pengeluaran"
    esc_desc = escape_html(desc)
    esc_cat = escape_html(cat_name)
    send(chat_id, f"✅ <b>{label}</b>\nRp {amt:,.0f}\n{esc_desc}\nKategori: {esc_cat}\n📅 {tgl}", parse_mode="HTML")

def get_fallback_category(user_id, tx_type):
    """Lookup fallback category by name and type, avoid hardcoded IDs"""
    name = "Lainnya (Pemasukan)" if tx_type == "I" else "Lainnya (Pengeluaran)"
    # Try user's category first, then global
    for uid in (user_id, 0):
        result = supabase_get("maskai_categories", {"user_id": f"eq.{uid}", "name": f"ilike.{name}", "type": f"eq.{tx_type}", "select": "id", "limit": "1"})
        cats = result.data if result.ok and isinstance(result.data, list) else []
        if cats:
            return cats[0]["id"]
    return None

def cmd_usage(chat_id):
    """Show Supabase usage stats — uses supabase_get"""
    send(chat_id, "⏳ Cek usage Supabase...")
    tables = {
        "maskai_transactions": "Transaksi",
        "maskai_debts": "Hutang/Piutang",
        "maskai_keranjang": "Keranjang",
        "maskai_categories": "Kategori",
        "maskai_balance": "Saldo"
    }
    total_rows = 0
    msg = "📊 <b>Supabase Usage</b>\n\n"
    for t, label in tables.items():
        result = supabase_get(t, {"select": "count"})
        if result.ok:
            ct = len(result.data) if isinstance(result.data, list) else "?"
            total_rows += ct if isinstance(ct, int) else 0
            msg += f"  {label}: {ct}\n"
        else:
            msg += f"  {label}: error ({result.status})\n"
    est_size_mb = (total_rows * 0.5) / 1024
    msg += f"\n📦 <b>Estimasi:</b>\n  Total rows: {total_rows}\n  Est. size: {est_size_mb:.1f} MB"
    send(chat_id, msg, parse_mode="HTML")

# ── Command Router ──

def cmd_status(chat_id, user_id):
    """Bot status — uses supabase_get"""
    import time as tm
    uptime = tm.strftime("%Hh %Mm", tm.gmtime(tm.time() - __import__('maskai.app').BOT_START_TIME))
    db = {}
    labels = {"maskai_transactions":"TX","maskai_debts":"Hutang","maskai_keranjang":"Keranjang","maskai_categories":"Kat"}
    for t, lbl in labels.items():
        result = supabase_get(t, {"select": "count"})
        if result.ok:
            db[lbl] = len(result.data) if isinstance(result.data, list) else "?"
        else:
            db[lbl] = f"err({result.status})"
    send(chat_id, f"📌 <b>MASKAI Bot v2</b>\n✅ Aktif\n⏱ {uptime}\n🧠 Teks: Claude Sonnet 4.5\n🖼 OCR: GPT-5.5\n\n💾 <b>Database:</b>\n TX: {db.get('TX','?')} | Hutang: {db.get('Hutang','?')}\n Keranjang: {db.get('Keranjang','?')} | Kat: {db.get('Kat','?')}", parse_mode="HTML")
