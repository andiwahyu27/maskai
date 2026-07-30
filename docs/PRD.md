# PRD: MASKAI Bot Dashboard

**Product:** MASKAI Bot Settings Dashboard
**Domain:** https://bot.maskai.my.id
**Date:** 2026-07-29
**Author:** Yang Mulia Andi

---

## 1. Overview
Web-based dashboard untuk mengelola bot MASKAI tanpa harus edit file di VPS. Bisa diakses dari HP/laptop.

## 2. User Story
Sebagai **admin MASKAI**, saya ingin:
- Lihat status bot & database realtime
- Edit konfigurasi (model AI, API key, dll)
- Kelola kategori (CRUD)
- Lihat transaksi & laporan visual
- Trigger sync ke Google Sheets
- Lihat log bot

## 3. Tech Stack
| Layer | Tech |
|-------|------|
| Frontend | HTML + Alpine.js + Tailwind CSS |
| Backend | Flask (Python) |
| Auth | Password + session cookie |
| Database | Supabase (existing) |

## 4. Pages

### 4.1 Dashboard (`/`)
- Status bot (online/offline, uptime)
- Model AI yang dipakai (teks + OCR)
- Statistik: total transaksi, saldo, 7-day chart
- Quick actions: `/sync`, `/restart`, `/backup`

### 4.2 Transaksi (`/transactions`)
- Table semua transaksi (sortable, filterable)
- Filter: tanggal, kategori, tipe (in/out)
- Export CSV
- Kolom: Tanggal, Jumlah, Kategori, Deskripsi, Tipe

### 4.3 Kategori (`/categories`)
- Table kategori + CRUD
- Tambah/edit icon, nama, tipe (I/E)
- Hapus kategori

### 4.4 Pengaturan (`/settings`)
- Model AI teks & OCR (dropdown)
- API keys (masked, editable)
- Google Sheets ID
- Admin chat ID
- Tombol save & test

### 4.5 Log (`/logs`)
- View last 200 lines from journalctl
- Auto-refresh tiap 30 detik
- Filter: error/warning/info

## 5. API Endpoints (Flask)

| Route | Method | Desc |
|-------|--------|------|
| `/api/status` | GET | Bot status + stats |
| `/api/transactions` | GET | List transaksi |
| `/api/categories` | GET/POST/PUT/DELETE | CRUD kategori |
| `/api/settings` | GET/POST | Get/save config |
| `/api/logs` | GET | Bot logs |
| `/api/sync` | POST | Trigger sync |
| `/api/restart` | POST | Restart bot |

## 6. MVP Checklist
- [ ] Flask server running on port 5000
- [ ] Auth login page
- [ ] Dashboard with stats
- [ ] Transaction table
- [ ] Category management
- [ ] Settings page
- [ ] Log viewer

## 7. File Structure
```
/home/ubuntu/maskai/web/
├── app.py          # Flask server
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── transactions.html
│   ├── categories.html
│   ├── settings.html
│   └── logs.html
├── static/
│   └── style.css
└── requirements.txt
```

## 8. Security
- Session-based auth with password
- All API calls go through Flask → Supabase (no client-side keys)
- CORS restricted to bot.maskai.my.id
- HTTPS via Caddy (already configured)
