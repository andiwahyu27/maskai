# MASKAI Database Schema

## Tables

### maskai_transactions
| Column | Type | Desc |
|--------|------|------|
| id | bigint PK | Auto-increment |
| user_id | bigint | Telegram user ID |
| type | char(1) | I=Pemasukan, E=Pengeluaran |
| amount | numeric | Jumlah |
| currency | varchar(3) | Default: IDR |
| category_id | bigint FK | → maskai_categories.id |
| description | text | Deskripsi transaksi |
| transaction_dt | timestamptz | Tanggal transaksi |
| is_reconciled | boolean | Default: false |
| metadata | jsonb | Data tambahan |
| created_at | timestamptz | Auto |
| updated_at | timestamptz | Auto |

### maskai_categories
| Column | Type | Desc |
|--------|------|------|
| id | bigint PK | Auto-increment |
| user_id | bigint | Default: 1367356347 |
| name | varchar(100) | Nama kategori |
| type | char(1) | I/E |
| icon | varchar(32) | Emoji, default: 📦 |
| parent_id | bigint | FK self |
| is_archived | boolean | Default: false |
| created_at | timestamptz | Auto |
| updated_at | timestamptz | Auto |

### maskai_debts
| Column | Type | Desc |
|--------|------|------|
| id | bigint PK | Auto-increment |
| user_id | bigint | Telegram user ID |
| counterparty | varchar(255) | Nama orang |
| direction | char(1) | O=Hutang, T=Piutang |
| amount | numeric | Jumlah |
| currency | varchar(3) | Default: IDR |
| description | text | Deskripsi |
| due_date | date | Jatuh tempo |
| status | varchar(20) | open/settled |
| amount_paid | numeric | Sudah dibayar |
| settled_at | timestamptz | Tanggal lunas |
| created_at | timestamptz | Auto |
| updated_at | timestamptz | Auto |

### maskai_keranjang
| Column | Type | Desc |
|--------|------|------|
| id | bigint PK | Auto-increment |
| user_id | bigint | Telegram user ID |
| amount | numeric | Jumlah |
| description | text | Deskripsi |
| is_fulfilled | boolean | Default: false |
| fulfilled_at | timestamptz | Tanggal teralisasi |
| created_at | timestamptz | Auto |

### maskai_balance (view)
Generated from trigger on transactions. Shows current balance per user.

## Default Categories
| ID | Icon | Name | Type |
|----|------|------|------|
| 1 | 🍽️ | Makanan & Minuman | E |
| 2 | 🚗 | Transportasi | E |
| 3 | 🛒 | Belanja | E |
| 4 | 📄 | Tagihan | E |
| 5 | 🎬 | Hiburan | E |
| 6 | 💊 | Kesehatan | E |
| 7 | 📚 | Pendidikan | E |
| 8 | 📦 | Lainnya (Pengeluaran) | E |
| 9 | 💰 | Gaji | I |
| 10 | 💼 | Freelance | I |
| 11 | 📈 | Investasi | I |
| 12 | 📦 | Lainnya (Pemasukan) | I |
