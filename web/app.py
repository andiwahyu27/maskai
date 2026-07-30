#!/usr/bin/env python3
"""MASKAI Dashboard - Flask web interface"""
import os, sys, json, time, requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "maskai-dashboard-secret-2026")

# ── Config ──
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pgnzzukciwtcxyzjuxlc.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DAHONO_KEY = os.environ.get("DAHONO_KEY", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "MaskaiAdmin_27")
SUPABASE_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

BOT_START_TIME = time.time()

# ── Auth ──
def login_required(f):
    @wraps(f)
    def wrap(*args, **kw):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kw)
    return wrap

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Password salah!")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── Pages ──
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/transactions")
@login_required
def transactions():
    return render_template("transactions.html")

@app.route("/categories")
@login_required
def categories():
    return render_template("categories.html")

@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")

@app.route("/logs")
@login_required
def logs():
    return render_template("logs.html")

# ── API ──
def supabase_get(table, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        q = "&".join(f"{k}={v}" for k, v in params.items())
        url += f"?{q}"
    try:
        r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10)
        return r.json() if r.text else []
    except:
        return []

def supabase_post(table, data):
    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", json=data, headers=SUPABASE_HEADERS, timeout=10)
        return r.json() if r.text else {}
    except:
        return {}

def supabase_patch(table, field, value, data):
    try:
        r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}?{field}=eq.{value}", json=data, headers=SUPABASE_HEADERS, timeout=10)
        return r.status_code in (200, 204)
    except:
        return False

def supabase_delete(table, field, value):
    try:
        r = requests.delete(f"{SUPABASE_URL}/rest/v1/{table}?{field}=eq.{value}", headers=SUPABASE_HEADERS, timeout=10)
        return r.status_code in (200, 204)
    except:
        return False

@app.route("/api/status")
@login_required
def api_status():
    uptime = int(time.time() - BOT_START_TIME)
    # Count rows
    counts = {}
    for t in ["maskai_transactions", "maskai_debts", "maskai_keranjang", "maskai_categories"]:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{t}?select=count",
            headers={**SUPABASE_HEADERS, "Prefer": "count=exact"}, timeout=5)
        counts[t] = r.headers.get("content-range", "").split("/")[-1]

    # Balance
    bal = supabase_get("maskai_balance", {"user_id": "eq.1367356347", "select": "balance"})
    balance = bal[0]["balance"] if bal else 0

    # Recent tx
    txs = supabase_get("maskai_transactions", {
        "user_id": "eq.1367356347", "select": "amount,type,transaction_dt",
        "order": "transaction_dt.desc", "limit": "7"
    })

    # Bot process
    bot_running = os.system("systemctl is-active --quiet maskai-bot.service") == 0

    return jsonify({
        "uptime": uptime,
        "bot_running": bot_running,
        "balance": balance,
        "counts": counts,
        "recent": txs
    })

@app.route("/api/transactions")
@login_required
def api_transactions():
    txs = supabase_get("maskai_transactions", {
        "user_id": "eq.1367356347",
        "select": "id,type,amount,description,transaction_dt,category_id",
        "order": "transaction_dt.desc",
        "limit": "100"
    })
    cats = {c["id"]: c["name"] for c in supabase_get("maskai_categories", {"select": "id,name"})}
    for t in txs:
        t["category_name"] = cats.get(t.get("category_id"), "-")
    return jsonify(txs)

@app.route("/api/categories", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
def api_categories():
    if request.method == "GET":
        cats = supabase_get("maskai_categories", {"select": "id,name,icon,type", "order": "id.asc"})
        return jsonify(cats)
    elif request.method == "POST":
        data = request.json
        result = supabase_post("maskai_categories", {
            "name": data["name"], "type": data["type"],
            "icon": data.get("icon", "📦"), "user_id": 1367356347
        })
        return jsonify({"ok": True})
    elif request.method == "PUT":
        data = request.json
        ok = supabase_patch("maskai_categories", "id", data["id"], {
            "name": data["name"], "icon": data.get("icon", "📦")
        })
        return jsonify({"ok": ok})
    elif request.method == "DELETE":
        cat_id = request.args.get("id")
        ok = supabase_delete("maskai_categories", "id", cat_id)
        return jsonify({"ok": ok})

@app.route("/api/settings", methods=["GET", "POST"])
@login_required
def api_settings():
    if request.method == "GET":
        return jsonify({
            "text_model": "dahono/claude-sonnet-4.5-free",
            "ocr_model": "dahono/gpt-5.5",
            "bot_token": BOT_TOKEN[:10] + "..." if BOT_TOKEN else "",
            "admin_id": "1367356347",
            "sheet_id": "1dBkYHEGsftjqH2NA9bd5EJ58Cc_HYKt8rVoWk0RdQUg"
        })
    else:
        # Save settings to .env file
        data = request.json
        with open("/home/ubuntu/maskai/.env", "w") as f:
            for k, v in data.items():
                f.write(f"{k}={v}\n")
        return jsonify({"ok": True})

@app.route("/api/logs")
@login_required
def api_logs():
    import subprocess
    lines = request.args.get("lines", "200")
    level = request.args.get("level", "")
    try:
        result = subprocess.run(
            ["journalctl", "-u", "maskai-bot.service", "--no-pager", "-n", lines],
            capture_output=True, text=True, timeout=10
        )
        logs = result.stdout
        if level and level != "all":
            logs = "\n".join(l for l in logs.split("\n") if level.upper() in l)
        return jsonify({"logs": logs[-5000:]})
    except:
        return jsonify({"logs": "Error reading logs"})

@app.route("/api/sync")
@login_required
def api_sync():
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("/home/ubuntu/maskai/service-account.json", scope)
        client = gspread.authorize(creds)
        
        sheet_id = "1dBkYHEGsftjqH2NA9bd5EJ58Cc_HYKt8rVoWk0RdQUg"
        sheet = client.open_by_key(sheet_id).sheet1
        
        txs = supabase_get("maskai_transactions", {
            "user_id": "eq.1367356347",
            "select": "id,type,amount,description,transaction_dt,category_id",
            "order": "id.asc"
        })
        cats = {c["id"]: c["name"] for c in supabase_get("maskai_categories", {"select": "id,name"})}
        
        sheet.clear()
        sheet.append_row(["ID", "Jenis", "Jumlah", "Kategori", "Deskripsi", "Tanggal"])
        
        rows = []
        for t in txs:
            rows.append([
                str(t["id"]),
                "Pemasukan" if t["type"] == "I" else "Pengeluaran",
                t["amount"],
                cats.get(t.get("category_id"), "-"),
                t.get("description", "-"),
                t["transaction_dt"][:10]
            ])
        
        for i in range(0, len(rows), 500):
            sheet.append_rows(rows[i:i+500])
        
        return jsonify({"ok": True, "count": len(txs)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/restart")
@login_required
def api_restart():
    os.system("sudo systemctl restart maskai-bot.service")
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
