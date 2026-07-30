# MASKAI Implementation Plan

**Tanggal:** 2026-07-30  
**Referensi:** `code_review.md`  
**Strategi:** patch minimal, testable, dan bertahap

## Prinsip implementasi

1. Security dan data integrity dikerjakan sebelum refactor.
2. Satu phase harus lulus test sebelum masuk phase berikutnya.
3. Hindari perubahan besar yang tidak diperlukan.
4. Pertahankan public behavior command Telegram.
5. Semua perubahan schema harus disertai migration note.
6. Setiap issue yang selesai dicatat di `resolved.md`.

---

## Phase 0 — Repository preparation

### Tasks

- [ ] Buat `docs/code-review/`.
- [ ] Simpan `code_review.md`.
- [ ] Simpan `implementation.md`.
- [ ] Buat `resolved.md`.
- [ ] Buat folder `tests/`.
- [ ] Tambahkan baseline test infrastructure dengan `unittest` atau `pytest`.
- [ ] Jalankan syntax check awal.

### Baseline validation

```bash
python -m py_compile bot.py
python -m unittest discover -s tests -v
```

### Definition of done

- Struktur repository tersedia.
- Existing bot dapat di-import dalam test tanpa menjalankan main loop.
- Baseline result dicatat.

---

## Phase 1 — Authorization boundary

**Issues:** CR-001

### Design

Tambahkan helper:

```python
def is_authorized(user_id: int) -> bool:
    return user_id in ADMIN_IDS
```

Authorization dilakukan sebelum photo handling, command routing, natural input, dan callback processing.

### Tasks

- [ ] Tambahkan helper authorization.
- [ ] Terapkan pada message.
- [ ] Terapkan pada callback query.
- [ ] Tambahkan contextual security log.
- [ ] Pastikan `/start` juga mengikuti sifat private bot.
- [ ] Tambahkan test unauthorized message.
- [ ] Tambahkan test unauthorized callback.
- [ ] Tambahkan test authorized message.

### Definition of done

- Tidak ada business function dipanggil untuk unauthorized user.
- Callback mutation tidak bisa dilewati.

---

## Phase 2 — API result model dan safe HTTP handling

**Issues:** CR-007, CR-013

### Design

Buat satu result type, misalnya:

```python
@dataclass
class ApiResult:
    ok: bool
    data: Any = None
    status_code: int | None = None
    error: str | None = None
```

Pisahkan concern:

- `http_get()`
- `http_post()`
- `http_delete()`
- `supabase_get()`
- `supabase_post()`
- `supabase_delete()`

### Tasks

- [ ] Tambahkan typed result.
- [ ] Handle timeout spesifik.
- [ ] Handle request exception.
- [ ] Handle invalid JSON.
- [ ] Handle non-2xx.
- [ ] Hilangkan bare `except`.
- [ ] Migrasikan caller secara bertahap.
- [ ] Pastikan log tidak mengandung secret.
- [ ] Tambahkan test timeout, invalid JSON, 400, dan 200.

### Trade-off

Mengubah return type dapat menyentuh banyak caller. Patch harus dilakukan konsisten dalam satu phase agar tidak ada campuran dictionary/result object yang membingungkan.

### Definition of done

- Mutasi database tidak lagi dianggap sukses tanpa bukti.
- Semua external request memiliki timeout dan error handling.

---

## Phase 3 — User ownership dan category safety

**Issues:** CR-002, CR-005, CR-006, CR-012

### Tasks

#### OCR ownership

- [ ] Ubah `cmd_ocr(chat_id, user_id, file_id, update_id=None)`.
- [ ] Teruskan `user_id` dari router.
- [ ] Hapus hardcoded user ID.

#### Category creation

- [ ] Ubah `cmd_tambahkat()` menerima `user_id`.
- [ ] Sertakan `user_id` dalam payload.
- [ ] Perbaiki parsing nama multi-word dan icon.
- [ ] Validasi hasil insert.

#### Ownership filters

- [ ] List hanya kategori global dan milik user.
- [ ] Edit/delete hanya kategori milik user.
- [ ] Global category read-only.
- [ ] Terapkan aturan pada callback.

#### Fallback category

- [ ] Buat helper lookup fallback category.
- [ ] Cari berdasarkan name/type/ownership.
- [ ] Hapus hardcoded ID 8 dan 9.
- [ ] Tangani fallback missing.

### Tests

- [ ] OCR menggunakan user pengirim.
- [ ] Tambah kategori menyertakan user.
- [ ] User tidak bisa edit/delete kategori lain.
- [ ] Global category tidak dapat dimutasi.
- [ ] Fallback tetap benar walau ID berubah.

### Definition of done

- Seluruh data user memiliki ownership boundary yang konsisten.

---

## Phase 4 — Query builder dan laporan timezone-aware

**Issues:** CR-003, CR-011

### Design

Gunakan list tuple untuk duplicate query keys:

```python
params = [
    ("user_id", f"eq.{user_id}"),
    ("transaction_dt", f"gte.{start_utc.isoformat()}"),
    ("transaction_dt", f"lt.{end_utc.isoformat()}"),
]
```

Gunakan `ZoneInfo("Asia/Jakarta")`.

### Tasks

- [ ] Ubah `supabase_get()` menerima dict dan list tuples, atau standardisasi list tuples.
- [ ] Gunakan URL encoding aman.
- [ ] Perbaiki custom date range.
- [ ] Implementasikan batas “hari ini”.
- [ ] Implementasikan batas “minggu ini”.
- [ ] Implementasikan batas “bulan ini”.
- [ ] Convert batas lokal ke UTC.
- [ ] Validasi input tanggal.
- [ ] Test duplicate params.
- [ ] Test midnight Jakarta.
- [ ] Test custom range inclusive date behavior.

### Definition of done

- Kedua batas tanggal selalu terkirim.
- Label periode sesuai calendar period, bukan rolling duration.

---

## Phase 5 — Input validation dan Telegram output safety

**Issues:** CR-008, CR-014

### Tasks

#### Amount validation

- [ ] Buat `parse_positive_amount()`.
- [ ] Gunakan `Decimal`.
- [ ] Validasi batas schema `NUMERIC(12,2)`.
- [ ] Terapkan pada natural input, OCR, debt, dan cart.

#### LLM/OCR payload validation

- [ ] Validasi root object.
- [ ] Validasi required fields.
- [ ] Normalisasi transaction type.
- [ ] Batasi description yang ekstrem.
- [ ] Tangani invalid content tanpa crash.

#### Telegram formatting

- [ ] Pilih HTML + `html.escape`, atau MarkdownV2 helper.
- [ ] Escape seluruh data dinamis.
- [ ] Jangan ubah command keyboard.
- [ ] Test special characters.

### Definition of done

- Invalid model output tidak mencapai database.
- Konten dinamis tidak merusak Telegram message.

---

## Phase 6 — Balance integrity migration

**Issues:** CR-004

### Database design

Trigger harus menangani:

- INSERT: tambahkan signed amount;
- DELETE: kurangi efek OLD;
- UPDATE: rollback OLD lalu terapkan NEW.

Pertimbangkan perubahan:

- amount;
- type;
- user_id;
- currency.

### Tasks

- [ ] Buat helper SQL apply delta.
- [ ] Replace trigger lama.
- [ ] Tambahkan function reset user data yang atomic.
- [ ] Gunakan RPC untuk `/resetdb`, atau dokumentasikan fallback.
- [ ] Buat reconciliation SQL untuk menghitung ulang balance existing.
- [ ] Uji dengan transaction SQL.

### Reconciliation query

Hermes harus membuat query yang menghitung ulang seluruh balance dari `maskai_transactions`, bukan hanya memperbaiki trigger untuk data baru.

### Migration safety

- Gunakan transaction.
- Backup atau tampilkan verification query.
- Jangan drop transaction data.
- Catat command deployment.

### Definition of done

- Balance sesuai agregasi transaction setelah INSERT, UPDATE, DELETE, dan reset.

---

## Phase 7 — Telegram idempotency dan persistent offset

**Issues:** CR-009, CR-010

### Idempotency design

Pilihan utama:

- simpan `telegram_update_id` di `metadata`;
- buat unique partial index.

Alternatif:

- tabel khusus processed updates.

Gunakan opsi metadata bila tidak ada kebutuhan audit lebih kompleks.

### Tasks

- [ ] Teruskan `update_id` ke `process()`.
- [ ] Teruskan ke transaction-producing commands.
- [ ] Simpan update ID di metadata.
- [ ] Tambahkan unique partial index.
- [ ] Handle conflict sebagai already processed.
- [ ] Buat persistent offset path configurable.
- [ ] Implementasikan atomic write.
- [ ] Handle offset corrupt.
- [ ] Dokumentasikan systemd permission/path.
- [ ] Test duplicate update.
- [ ] Test offset read/write.

### Trade-off

Offset saja tidak cukup untuk exactly-once processing. Database idempotency tetap diperlukan karena crash dapat terjadi setelah insert tetapi sebelum offset write.

### Definition of done

- Retry update tidak membuat transaksi ganda.
- Reboot tidak menghilangkan polling state.

---

## Phase 8 — Regression review

### Tasks

- [ ] Jalankan seluruh test.
- [ ] Jalankan syntax check.
- [ ] Review seluruh command:
  - `/start`
  - `/menu`
  - `/saldo`
  - `/hutang`
  - `/piutang`
  - `/keranjang`
  - `/kategori`
  - `/editkat`
  - `/hapuskat`
  - `/tambahkat`
  - `/laporan`
  - `/status`
  - `/usage`
  - `/sync`
  - `/resetdb`
  - `/stop`
  - natural input
  - photo OCR
- [ ] Pastikan model dan endpoint tidak berubah.
- [ ] Pastikan tidak ada secret di diff.
- [ ] Isi `resolved.md`.

### Required output in `resolved.md`

```markdown
# Resolved Review Issues

## CR-001
Status: Done
Files:
- bot.py
- tests/test_bot.py

Validation:
- test_unauthorized_message: passed
- test_unauthorized_callback: passed

Notes:
- Authorization dilakukan sebelum routing.
```

### Final commands

```bash
python -m py_compile bot.py
python -m unittest discover -s tests -v
git diff --check
git status --short
```

---

## Suggested commit sequence

```text
Add code review documentation
Add bot authorization guard
Standardize API error handling
Fix user ownership and categories
Fix report date filters and timezone
Validate AI transaction payloads
Fix balance trigger consistency
Add Telegram update idempotency
Add bot regression tests
```

Commit dapat digabung bila repository kecil, tetapi setiap commit harus tetap reviewable.

---

## Completion checklist

- [ ] CR-001 selesai
- [ ] CR-002 selesai
- [ ] CR-003 selesai
- [ ] CR-004 selesai
- [ ] CR-005 selesai
- [ ] CR-006 selesai
- [ ] CR-007 selesai
- [ ] CR-008 selesai
- [ ] CR-009 selesai
- [ ] CR-010 selesai
- [ ] CR-011 selesai
- [ ] CR-012 selesai
- [ ] CR-013 selesai
- [ ] CR-014 selesai
- [ ] Semua test lulus
- [ ] Migration tervalidasi
- [ ] `resolved.md` lengkap
