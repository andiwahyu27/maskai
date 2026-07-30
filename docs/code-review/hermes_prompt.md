# Prompt untuk Hermes AI — Setup Repository dan Implementasi Review MASKAI

Kamu bertindak sebagai senior Python engineer yang mengerjakan repository MASKAI.

## Tujuan

1. Rapikan repository agar dokumentasi code review tersimpan secara versioned.
2. Baca seluruh isi:
   - `docs/code-review/code_review.md`
   - `docs/code-review/implementation.md`
3. Implementasikan seluruh issue sesuai urutan prioritas.
4. Jangan mengubah behavior lain di luar scope review.
5. Setelah setiap tahap, lakukan self-review dan tampilkan ringkasan perubahan.

## Struktur repository yang harus dibuat

```text
maskai/
├── bot.py
├── schema.sql
├── web/
│   └── app.py
├── docs/
│   └── code-review/
│       ├── code_review.md
│       ├── implementation.md
│       └── resolved.md
└── tests/
    └── test_bot.py
```

Jika folder `docs/code-review/` atau `tests/` belum ada, buat folder tersebut.

## Aturan pengerjaan

- Kerjakan issue berdasarkan priority: P0 → P1 → P2.
- Jangan menghapus fitur yang sudah ada.
- Jangan mengganti model AI, endpoint, token, nama tabel, atau command Telegram tanpa alasan yang tertulis di review.
- Jangan hardcode secret baru.
- Semua external HTTP request harus memiliki timeout.
- Semua response JSON harus diparsing dengan error handling.
- Jangan memakai bare `except`.
- Gunakan logging dengan context, tetapi jangan log token, API key, atau data sensitif.
- Pertahankan compatibility Python 3.11.
- Pertahankan nama command Telegram yang sudah ada.
- Gunakan timezone-aware datetime.
- Semua mutasi database harus memeriksa hasil operasi sebelum memberi pesan sukses ke pengguna.
- Untuk perubahan schema, buat SQL yang aman dijalankan ulang sebisa mungkin.
- Jangan langsung melakukan refactor besar ke banyak module. Fokus dulu ke correctness dan security.

## Workflow wajib

### 1. Analisis awal

Sebelum mengubah file:

- Baca `bot.py`, `schema.sql`, `code_review.md`, dan `implementation.md`.
- Cocokkan setiap issue dengan kode aktual.
- Catat bila ada issue yang sudah tidak relevan karena kode telah berubah.

### 2. Implementasi

Kerjakan satu phase pada satu waktu.

Untuk setiap issue:

1. Jelaskan akar masalah secara singkat.
2. Terapkan patch minimal.
3. Tambahkan atau perbarui test.
4. Jalankan test dan syntax check.
5. Catat hasilnya di `docs/code-review/resolved.md`.

### 3. Validasi

Minimal jalankan:

```bash
python -m py_compile bot.py
python -m unittest discover -s tests -v
```

Jika `pytest` tersedia, boleh gunakan:

```bash
pytest -q
```

Validasi tambahan:

- pastikan unauthorized user ditolak;
- pastikan callback query juga melakukan authorization;
- pastikan OCR menggunakan `user_id` pengirim;
- pastikan filter laporan date range mengirim kondisi awal dan akhir;
- pastikan insert gagal tidak menghasilkan pesan sukses;
- pastikan reset/delete/update transaksi tidak meninggalkan saldo stale;
- pastikan duplicate Telegram update tidak membuat transaksi ganda;
- pastikan offset disimpan secara persistent dan atomic;
- pastikan waktu laporan menggunakan Asia/Jakarta;
- pastikan output dinamis Telegram tidak merusak formatting.

### 4. Output akhir

Setelah selesai, berikan:

- daftar file yang berubah;
- ringkasan perubahan per issue ID;
- test yang dijalankan dan hasilnya;
- migration SQL yang perlu dijalankan;
- risiko atau pekerjaan lanjutan;
- unified diff atau ringkasan diff yang mudah direview.

## Guardrail

Berhenti dan laporkan, jangan menebak, bila:

- schema produksi berbeda dari `schema.sql`;
- tabel atau column yang diperlukan tidak ditemukan;
- perubahan membutuhkan secret atau akses eksternal;
- migrasi berisiko destructive;
- requirement di `code_review.md` bertentangan dengan kode terbaru.

## Definition of Done

Pekerjaan dianggap selesai bila:

- seluruh issue P0 selesai;
- seluruh issue P1 selesai atau diberi alasan teknis yang jelas;
- test utama lulus;
- tidak ada syntax error;
- `resolved.md` berisi status tiap issue;
- tidak ada secret yang masuk Git;
- behavior command lama tetap kompatibel.
