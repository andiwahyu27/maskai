# MASKAI Code Review

**Tanggal:** 2026-07-30  
**Scope utama:** `bot.py`, `schema.sql`  
**Reviewer:** MASKAI Assistant  
**Status:** Open

## Ringkasan

Review menemukan risiko pada authorization, isolasi data pengguna, query laporan, konsistensi saldo, validasi hasil AI, idempotency Telegram update, dan error handling API.

Prioritas:

- **P0:** keamanan dan data integrity;
- **P1:** reliability dan correctness;
- **P2:** maintainability dan user experience.

---

## P0 — Critical

### CR-001 — Bot tidak membatasi akses pengguna

**Severity:** Critical  
**File:** `bot.py`  
**Area:** `process()`, callback query handler

#### Problem

Sebagian besar command dapat dipakai pengguna Telegram mana pun. Hanya `/resetdb` dan `/stop` yang memeriksa `ADMIN_IDS`.

Pengguna tidak sah berpotensi:

- membuat transaksi;
- mengirim OCR;
- menambah, mengedit, atau menghapus kategori;
- menjalankan sync;
- melihat data laporan.

Karena backend menggunakan Supabase service role, pembatasan RLS tidak boleh dianggap sebagai lapisan proteksi.

#### Required change

- Tambahkan helper authorization terpusat.
- Tolak message dari `user_id` yang tidak terdaftar.
- Tolak callback query dari user yang tidak terdaftar.
- Log unauthorized attempt tanpa data sensitif.
- Berikan pesan aman kepada user.

#### Acceptance criteria

- Unauthorized message tidak memanggil business logic.
- Unauthorized callback tidak menjalankan mutasi.
- Authorized admin tetap dapat memakai seluruh command.
- Test mencakup message dan callback unauthorized.

---

### CR-002 — OCR menyimpan transaksi ke user hardcoded

**Severity:** Critical  
**File:** `bot.py`  
**Area:** `cmd_ocr()`

#### Problem

Insert OCR memakai:

```python
"user_id": 1367356347
```

Akibatnya transaksi OCR tidak menggunakan identitas pengirim.

#### Required change

- Ubah signature menjadi menerima `user_id`.
- Teruskan `user_id` dari `process()`.
- Hilangkan hardcoded user ID pada transaksi OCR.
- Sertakan metadata source bila implementasi metadata dilakukan.

#### Acceptance criteria

- OCR menyimpan transaksi ke user pengirim.
- Tidak ada hardcoded admin ID di payload OCR.
- Test memverifikasi payload insert.

---

### CR-003 — Filter date range `/laporan` kehilangan batas awal

**Severity:** Critical  
**File:** `bot.py`  
**Area:** `cmd_laporan()`, `supabase_get()`

#### Problem

Dictionary query menggunakan key `transaction_dt` dua kali. Python mempertahankan hanya value terakhir, sehingga filter `gte` hilang.

#### Required change

- Ubah query builder agar menerima duplicate query keys.
- Gunakan list of tuples atau mekanisme setara.
- Encode query dengan benar.
- Untuk rentang tanggal, gunakan batas awal dan batas akhir eksplisit.
- Prefer `gte start` dan `lt next_day` untuk batas akhir yang konsisten.

#### Acceptance criteria

- URL atau request params berisi dua filter `transaction_dt`.
- Transaksi sebelum tanggal awal tidak masuk.
- Transaksi setelah batas akhir tidak masuk.
- Test mencakup date range.

---

### CR-004 — Balance stale setelah delete atau update transaksi

**Severity:** Critical  
**File:** `schema.sql`, `bot.py`  
**Area:** trigger balance, `/resetdb`

#### Problem

Trigger balance hanya menangani `AFTER INSERT`. Delete dan update transaksi tidak mengoreksi saldo.

`/resetdb` menghapus transaksi tetapi balance dapat tetap menyimpan nilai lama.

#### Required change

- Ubah trigger agar menangani INSERT, UPDATE, dan DELETE.
- Untuk UPDATE, rollback dampak OLD lalu terapkan NEW.
- Untuk DELETE, balikkan dampak transaksi lama.
- Reset database sebaiknya atomic melalui SQL function/RPC.
- Migration harus aman dan terdokumentasi.

#### Acceptance criteria

- Insert mengubah saldo dengan benar.
- Delete membalikkan saldo.
- Update amount/type/user mengoreksi saldo.
- Reset user menghasilkan saldo yang benar.
- SQL migration tersedia.

---

## P1 — High

### CR-005 — `/tambahkat` tidak mengirim `user_id`

**Severity:** High  
**File:** `bot.py`  
**Area:** `cmd_tambahkat()`

#### Problem

Schema mewajibkan `user_id`, tetapi payload insert kategori tidak menyertakannya.

Bot tetap mengirim pesan berhasil walaupun insert gagal.

#### Required change

- Teruskan `user_id` ke `cmd_tambahkat()`.
- Sertakan `user_id` dalam insert.
- Periksa hasil operasi sebelum mengirim pesan sukses.
- Pertahankan dukungan nama kategori lebih dari satu kata.

#### Acceptance criteria

- Insert kategori memenuhi schema.
- Nama kategori multi-word tidak terpotong.
- Pesan sukses hanya muncul bila insert sukses.

---

### CR-006 — Operasi kategori tidak memiliki ownership filter

**Severity:** High  
**File:** `bot.py`  
**Area:** list, edit, delete kategori, callback

#### Problem

Query kategori mengambil kategori global dan user lain tanpa boundary yang jelas. Edit/delete hanya memfilter berdasarkan `id`.

#### Required change

- List kategori hanya menampilkan kategori yang diizinkan.
- Edit/delete harus memfilter `id` dan `user_id`.
- Kategori global `user_id=0` harus read-only, kecuali requirement berbeda.
- Callback delete mengikuti aturan ownership yang sama.

#### Acceptance criteria

- User tidak dapat mengubah kategori user lain.
- Kategori global tidak dapat dihapus/edit melalui bot.
- Test mencakup ownership.

---

### CR-007 — Mutasi database tidak diperiksa sebelum pesan sukses

**Severity:** High  
**File:** `bot.py`  
**Area:** natural input, OCR, debt, cart, category

#### Problem

Banyak command memanggil Supabase lalu langsung mengirim pesan sukses tanpa memeriksa HTTP status atau payload error.

#### Required change

- Standardisasi return result API.
- Bedakan success, HTTP failure, timeout, invalid JSON.
- Semua command mutasi wajib memeriksa hasil.
- Log failure dengan context command dan user ID.
- Jangan kirim raw exception atau response sensitif ke user.

#### Acceptance criteria

- Failed insert menghasilkan pesan gagal.
- Successful insert menghasilkan pesan sukses.
- Timeout dan invalid JSON tidak crash.
- Tidak ada bare `except`.

---

### CR-008 — Output LLM dan OCR tidak divalidasi

**Severity:** High  
**File:** `bot.py`  
**Area:** `cmd_natural()`, `cmd_ocr()`

#### Problem

Nilai `jumlah`, `total`, tipe transaksi, dan field teks dipercaya langsung dari model.

Risiko:

- amount nol atau negatif;
- tipe data salah;
- jumlah di luar batas schema;
- category tidak valid;
- runtime formatting error;
- insert ditolak tetapi user mendapat sukses.

#### Required change

- Validasi JSON shape.
- Gunakan decimal-safe amount parser.
- Pastikan amount lebih dari nol dan sesuai batas database.
- Normalisasi tipe transaksi.
- Batasi panjang deskripsi bila diperlukan.
- Fallback category harus valid.

#### Acceptance criteria

- Invalid amount ditolak sebelum insert.
- Missing field ditangani tanpa crash.
- Valid payload tetap berjalan.
- Test mencakup string, null, negatif, nol, dan jumlah valid.

---

### CR-009 — Telegram update belum idempotent

**Severity:** High  
**File:** `bot.py`, `schema.sql`  
**Area:** polling loop, insert transaksi

#### Problem

Jika transaksi berhasil disimpan tetapi proses mati sebelum offset disimpan, update yang sama dapat diproses ulang dan membuat transaksi duplikat.

#### Required change

- Teruskan `update_id` ke business flow.
- Simpan `telegram_update_id` dalam metadata transaksi atau tabel processing.
- Tambahkan unique constraint/index yang sesuai.
- Perlakukan conflict sebagai already processed.
- Pastikan retry tidak membuat transaksi ganda.

#### Acceptance criteria

- Update Telegram yang sama hanya membuat satu transaksi.
- Retry setelah simulated crash aman.
- Migration SQL tersedia.

---

## P2 — Medium

### CR-010 — Offset disimpan di `/tmp`

**Severity:** Medium  
**File:** `bot.py`  
**Area:** polling state

#### Problem

`/tmp/maskai_offset.txt` dapat hilang saat reboot atau cleanup.

#### Required change

- Gunakan path persistent dari environment variable.
- Default ke `/var/lib/maskai-bot/telegram-offset.txt`.
- Tulis file secara atomic.
- Handle file corrupt tanpa crash.
- Dokumentasikan permission systemd.

#### Acceptance criteria

- Offset bertahan setelah restart.
- Atomic write digunakan.
- Invalid file ditangani aman.

---

### CR-011 — Periode laporan tidak memakai timezone Asia/Jakarta

**Severity:** Medium  
**File:** `bot.py`  
**Area:** `cmd_laporan()`, timestamps

#### Problem

`datetime.utcnow()` menghasilkan rolling duration dan tidak merepresentasikan hari kalender Jakarta.

#### Required change

- Gunakan timezone-aware datetime.
- Gunakan `ZoneInfo("Asia/Jakarta")`.
- Definisikan:
  - hari ini berdasarkan midnight Jakarta;
  - minggu ini dengan aturan yang terdokumentasi;
  - bulan ini berdasarkan awal bulan.
- Convert batas query ke UTC.

#### Acceptance criteria

- “Hari ini” berarti tanggal lokal Jakarta.
- Query menggunakan aware datetime.
- Test mencakup boundary midnight.

---

### CR-012 — Fallback category memakai ID hardcoded

**Severity:** Medium  
**File:** `bot.py`  
**Area:** natural input, OCR

#### Problem

Fallback category menggunakan ID `8` dan `9`. ID tidak stabil antar environment.

#### Required change

- Cari fallback berdasarkan `user_id`, `name`, dan `type`.
- Dukung kategori global `user_id=0`.
- Jika fallback tidak ditemukan, jangan insert transaksi invalid.

#### Acceptance criteria

- Tidak ada fallback category ID hardcoded.
- Fallback bekerja walau ID category berubah.
- Missing fallback menghasilkan error yang jelas.

---

### CR-013 — Error handling HTTP dan JSON belum konsisten

**Severity:** Medium  
**File:** `bot.py`  
**Area:** `claude()`, delete request, status request, polling

#### Problem

Beberapa request mengakses `.json()` atau response nested tanpa handling yang memadai. Terdapat bare `except`.

#### Required change

- Tangkap exception spesifik.
- Semua request memiliki timeout.
- Parsing JSON dilindungi `ValueError`.
- Log endpoint/context tanpa secret.
- Standardisasi response result.

#### Acceptance criteria

- Tidak ada bare `except`.
- Invalid JSON tidak crash.
- HTTP non-2xx tidak dianggap sukses.

---

### CR-014 — Konten dinamis tidak di-escape untuk Telegram markup

**Severity:** Medium  
**File:** `bot.py`  
**Area:** seluruh response dinamis

#### Problem

Nama kategori, deskripsi, toko, dan item dari user/AI dimasukkan ke Markdown tanpa escaping.

#### Required change

- Pilih satu strategi:
  - HTML parse mode dengan `html.escape`, atau
  - MarkdownV2 dengan escape helper lengkap.
- Terapkan pada seluruh konten dinamis.
- Static message boleh tetap menggunakan format lama jika aman.

#### Acceptance criteria

- Deskripsi berisi `*`, `_`, `[`, `<`, `&` tidak menyebabkan send failure.
- Formatting pesan tetap terbaca.

---

## Non-goals

Review ini tidak meminta:

- mengganti Telegram polling menjadi webhook;
- mengganti Dahono atau model AI;
- memigrasikan bot ke framework lain;
- memecah `bot.py` menjadi banyak module;
- mengubah tampilan dashboard;
- menambah fitur finansial baru.

---

## Validation checklist

- [ ] `python -m py_compile bot.py`
- [ ] Unit test authorization
- [ ] Unit test OCR user ownership
- [ ] Unit test duplicate query params
- [ ] Unit test API result handling
- [ ] Unit test invalid LLM amount
- [ ] Unit test idempotency
- [ ] Unit test timezone boundaries
- [ ] SQL trigger diuji untuk INSERT
- [ ] SQL trigger diuji untuk UPDATE
- [ ] SQL trigger diuji untuk DELETE
- [ ] Tidak ada secret baru di repository
