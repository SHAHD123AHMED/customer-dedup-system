# وظيفته: الحارس. يقرأ ملف CSV، يصنّف كل سجل، ويحفظه في القاعدة السحابية
#   accepted -> جدول customers
#   duplicate / invalid -> جدول rejected_records
#   needs review -> جدول review_queue
# التشغيل العادي: بياخد customers.csv
# أو تكتب اسم ملف تاني: main.py new_batch.csv
import csv
import sys
import psycopg2

def normalize_email(email):
    return email.strip().lower()

def normalize_phone(phone):
    return "".join(ch for ch in phone if ch.isdigit())

def is_valid(name, email):
    if name.strip() == "":
        return False
    if "@" not in email or "." not in email:
        return False
    return True

input_file = sys.argv[1] if len(sys.argv) > 1 else "customers.csv"

with open("db_url.txt") as f:
    db_url = f.read().strip()

conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        full_name TEXT,
        email TEXT UNIQUE,
        phone TEXT
    )
""")
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
conn.commit()

accepted = duplicates = invalid = review = 0

with open(input_file, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        name = row["full_name"].strip()
        email = normalize_email(row["email"])
        phone = normalize_phone(row["phone"])

        # 1) صلاحية
        if not is_valid(name, email):
            invalid += 1
            cur.execute(
                "INSERT INTO rejected_records (full_name, email, phone, reason) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (name, email, phone, "invalid"))
            continue

        # 2) نفس الإيميل؟ مكرر مؤكد
        cur.execute("SELECT 1 FROM customers WHERE email = %s", (email,))
        if cur.fetchone():
            duplicates += 1
            cur.execute(
                "INSERT INTO rejected_records (full_name, email, phone, reason) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (name, email, phone, "duplicate"))
            continue

        # 3) نفس التليفون بإيميل مختلف؟ راجعني
        if phone:
            cur.execute("SELECT 1 FROM customers WHERE phone = %s", (phone,))
            if cur.fetchone():
                review += 1
                cur.execute(
                    "INSERT INTO review_queue (full_name, email, phone, reason) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (name, email, phone, "same_phone_different_email"))
                continue

        # 4) جديد: يتقبل
        cur.execute(
            "INSERT INTO customers (full_name, email, phone) VALUES (%s, %s, %s)",
            (name, email, phone))
        accepted += 1

conn.commit()

print("File      :", input_file)
print("Accepted  :", accepted)
print("Duplicates:", duplicates)
print("Invalid   :", invalid)
print("Review    :", review)
print()
print("--- Rows now in CLOUD database ---")
for table in ["customers", "rejected_records", "review_queue"]:
    cur.execute("SELECT COUNT(*) FROM " + table)
    print(table, ":", cur.fetchone()[0])

conn.close()