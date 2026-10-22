# Customer Deduplication System

A data redundancy removal system that validates every incoming customer record, classifies it as **accepted, duplicate, invalid, or needs review**, and only appends unique, verified records to a cloud PostgreSQL database (Neon).
## 🚀 Try it live
👉 **[Open the registration form](https://customer-dedup-system-qp9xa.faable.link/)**

Try registering the same email twice, or a phone number with letters, and watch the system classify each case.

🔗 **Live demo:** https://customer-dedup-system-qp9xa.faable.link/

> Built as part of the CodeAlpha internship, Task 1: Data Redundancy Removal System.

---

## How it works: the 3-gate pipeline

Every record (from a CSV file or from the web form) goes through the same pipeline in `dedup.py`:

| Gate | Check | Result |
|------|-------|--------|
| **1. Regex validation** | Name not empty, valid email format, valid Egyptian mobile number (11 digits), no letters in phone | `invalid` → `rejected_records` |
| **2. SHA-256 exact match** | Hash of `name + email + phone` already exists in the database | `duplicate` → `rejected_records` |
| **3. Fuzzy matching (rapidfuzz)** | Compared only against rows sharing the same email or phone | see below |

**Gate 3 decisions:**

- Name similarity **> 95%** → `duplicate` (rejected)
- Similarity **80% to 95%** → `needs review` (`review_queue`)
- Same email with a different name, or same phone with a different email → `needs review`
- No similar candidate → **accepted** and added to `customers`

The `review_queue` is how the system handles **false positives**: records that look like duplicates but might be different real people (for example, two family members sharing a phone number) are held for human review instead of being rejected.

Before any check, data is normalized: names and emails are lowercased and trimmed, and phone numbers are reduced to digits (`+20 10...` becomes `010...`).

---

## Task requirements → how they are met

| Requirement | Implementation |
|---|---|
| Identify and classify redundant data / false positives | 4 classes: accepted, duplicate, invalid, review. Borderline cases go to `review_queue` |
| Validate new data against existing data | Gates 2 and 3 compare every new record with the cloud database **before** insertion |
| Prevent duplicates from entering the cloud database | Database-level protection: `UNIQUE` on `email`, unique index on `row_hash`, plus `ON CONFLICT DO NOTHING` for concurrent requests |
| Append only unique and verified entries | Only records that pass all 3 gates are inserted into `customers`; everything else is logged with its reason |
| Database accuracy and efficiency | Indexes on `email`, `phone`, `row_hash`. Fuzzy matching runs only on a small candidate set, never a full table scan. `find_duplicates.py` cleans old duplicates |

---

## Database schema

| Table | Purpose |
|---|---|
| `customers` | Clean, unique, verified records |
| `rejected_records` | Invalid and duplicate records, with the reason for each |
| `review_queue` | Suspicious records waiting for human review |

---

## Project structure

```
├── dedup.py              # Core logic: the 3 gates + table setup (single source of truth)
├── main.py               # Batch mode: processes a CSV file
├── app.py                # Web mode: Flask registration form + /submit API
├── find_duplicates.py    # Cleanup tool for old duplicates (dry-run by default)
├── generate_data.py      # TODO: describe in one line
├── benchmark.py          # TODO: describe in one line
├── customers.csv         # Sample dataset
└── requirements.txt
```

`main.py` and `app.py` both call `dedup.process_record()`, so the CSV flow and the web form always behave identically.

---

## Setup

```bash
git clone https://github.com/SHAHD123AHMED/customer-dedup-system.git
cd customer-dedup-system
pip install -r requirements.txt
```

Provide your Neon connection string in **one** of two ways:

- Environment variable: `DATABASE_URL`
- Or a local file `db_url.txt` containing only the connection string (this file is git-ignored)

## Usage

**Process a CSV file:**
```bash
python main.py                  # uses customers.csv
python main.py new_batch.csv    # or any other file
```

**Run the web form:**
```bash
python app.py
# open http://localhost:5000
```

**Find and clean old duplicates:**
```bash
python find_duplicates.py            # preview only, changes nothing
python find_duplicates.py --apply    # move duplicates to rejected_records
```

---

## Example result

Running a 130-row file against a database that already contained its records:

```
Total     : 130
Accepted  : 0        <- nothing was added twice
Duplicates: 121
Invalid   : 6
Review    : 3
customers : 101      <- unique rows in the cloud database
```

Re-running the same file never creates duplicates.

---

## Known limitations

- Fuzzy matching only compares against rows sharing the same email or phone (a deliberate choice for speed). Two similar names with a different email **and** a different phone are treated as different people.
- Phone validation targets Egyptian mobile numbers only.
- Name similarity uses `rapidfuzz.fuzz.ratio`, so very different spellings of the same name (for example transliteration variants) may not be caught.

## Tech stack

Python · Flask · PostgreSQL (Neon) · psycopg2 · rapidfuzz · hashlib (SHA-256) · regex · deployed on Faable
