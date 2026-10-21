# وظيفته: منطق التصنيف الوحيد في المشروع (البوابات التلاتة).
import hashlib
import re
from rapidfuzz import fuzz

EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)*\.[a-z]{2,}$")
PHONE_RE = re.compile(r"^01[0125]\d{8}$")

REJECT_ABOVE = 95
REVIEW_FROM = 80


def normalize_name(name):
    return " ".join(name.strip().lower().split())


def normalize_email(email):
    return email.strip().lower()


def normalize_phone(phone):
    digits = "".join(ch for ch in phone if ch.isdigit())
    if digits.startswith("20") and len(digits) == 12:
        digits = "0" + digits[2:]
    return digits


def make_hash(name, email, phone):
    text = name + "|" + email + "|" + phone
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_valid(name, email, phone, raw_phone):
    if name == "":
        return False, "invalid: empty name"
    if not EMAIL_RE.match(email):
        return False, "invalid: bad email"
    if any(ch.isalpha() for ch in raw_phone):
        return False, "invalid: phone has letters"
    if not PHONE_RE.match(phone):
        return False, "invalid: bad phone"
    return True, ""


def ensure_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            full_name TEXT,
            email TEXT UNIQUE,
            phone TEXT
        )
    """)
    cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS row_hash TEXT")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_hash ON customers (row_hash)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers (phone)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rejected_records (
            id SERIAL PRIMARY KEY,
            full_name TEXT, email TEXT, phone TEXT, reason TEXT,
            UNIQUE (full_name, email, phone, reason)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS review_queue (
            id SERIAL PRIMARY KEY,
            full_name TEXT, email TEXT UNIQUE, phone TEXT, reason TEXT
        )
    """)


def _reject(cur, name, email, phone, reason):
    cur.execute(
        "INSERT INTO rejected_records (full_name, email, phone, reason) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (name, email, phone, reason))


def process_record(cur, raw_name, raw_email, raw_phone):
    name = normalize_name(raw_name)
    email = normalize_email(raw_email)
    phone = normalize_phone(raw_phone)

    ok, why = is_valid(name, email, phone, raw_phone)
    if not ok:
        _reject(cur, name, email, phone, why)
        return "invalid", why

    row_hash = make_hash(name, email, phone)
    cur.execute("SELECT 1 FROM customers WHERE row_hash = %s", (row_hash,))
    if cur.fetchone():
        why = "duplicate: exact match (hash)"
        _reject(cur, name, email, phone, why)
        return "duplicate", why

    cur.execute(
        "SELECT full_name, email, phone FROM customers "
        "WHERE email = %s OR phone = %s", (email, phone))
    candidates = cur.fetchall()

    if candidates:
        best = max(fuzz.ratio(name, c[0]) for c in candidates)
        same_email = any(c[1] == email for c in candidates)

        if best > REJECT_ABOVE:
            why = "duplicate: similar %d%%" % best
            _reject(cur, name, email, phone, why)
            return "duplicate", why

        if best >= REVIEW_FROM:
            why = "needs review: similar name %d%%" % best
        elif same_email:
            why = "needs review: same email, different name"
        else:
            why = "needs review: same phone, different email"

        cur.execute(
            "INSERT INTO review_queue (full_name, email, phone, reason) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (name, email, phone, why))
        return "review", why

    cur.execute(
        "INSERT INTO customers (full_name, email, phone, row_hash) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
        (name, email, phone, row_hash))
    if cur.fetchone() is None:
        why = "duplicate: blocked by database"
        _reject(cur, name, email, phone, why)
        return "duplicate", why
    return "accepted", ""