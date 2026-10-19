# وظيفته: صفحة ويب فيها فورم تسجيل عميل + خدمة بترد فوراً (نفس منطق الحارس)
from flask import Flask, request, jsonify
import psycopg2
import psycopg2.errors

app = Flask(__name__)

import os

DB_URL = os.environ.get("DB_URL")          # على السحابة: من إعدادات المنصة
if not DB_URL:                             # على جهازك: من الملف
    with open("db_url.txt") as f:
        DB_URL = f.read().strip()


def get_connection():
    return psycopg2.connect(DB_URL)


def create_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            full_name TEXT, email TEXT UNIQUE, phone TEXT
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
    conn.close()


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


def process(name, email, phone):
    """نفس منطق الحارس. بيرجّع (الحالة، الرسالة)."""
    name = name.strip()
    email = normalize_email(email)
    phone = normalize_phone(phone)

    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1) صلاحية
        if not is_valid(name, email):
            cur.execute(
                "INSERT INTO rejected_records (full_name, email, phone, reason) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (name, email, phone, "invalid"))
            conn.commit()
            return "invalid", "البيانات غير صحيحة: اكتب الاسم وإيميل صحيح."

        # 2) نفس الإيميل؟ مكرر مؤكد
        cur.execute("SELECT 1 FROM customers WHERE email = %s", (email,))
        if cur.fetchone():
            cur.execute(
                "INSERT INTO rejected_records (full_name, email, phone, reason) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (name, email, phone, "duplicate"))
            conn.commit()
            return "duplicate", "الإيميل ده مسجّل عندنا قبل كده."

        # 3) نفس التليفون بإيميل مختلف؟ راجعني
        if phone:
            cur.execute("SELECT 1 FROM customers WHERE phone = %s", (phone,))
            if cur.fetchone():
                cur.execute(
                    "INSERT INTO review_queue (full_name, email, phone, reason) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (name, email, phone, "same_phone_different_email"))
                conn.commit()
                return "review", "رقم التليفون ده مسجّل بإيميل تاني. هنراجع بياناتك ونرد عليك."

        # 4) جديد: يتسجل
        try:
            cur.execute(
                "INSERT INTO customers (full_name, email, phone) VALUES (%s, %s, %s)",
                (name, email, phone))
            conn.commit()
            return "accepted", "تم التسجيل بنجاح. أهلاً بيك!"
        except psycopg2.errors.UniqueViolation:
            # لو حد سجّل نفس الإيميل في نفس اللحظة، القاعدة نفسها بتمنعه
            conn.rollback()
            return "duplicate", "الإيميل ده مسجّل عندنا قبل كده."
    finally:
        conn.close()


PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>تسجيل عميل جديد</title>
<style>
  body { font-family: Tahoma, Arial, sans-serif; background:#f3f4f6; margin:0; padding:30px; }
  .card { max-width:420px; margin:auto; background:#fff; padding:24px; border-radius:12px;
          box-shadow:0 2px 8px rgba(0,0,0,.1); }
  h2 { margin-top:0; }
  label { display:block; margin:12px 0 4px; font-weight:bold; }
  input { width:100%; padding:10px; border:1px solid #ccc; border-radius:6px; box-sizing:border-box; }
  button { width:100%; margin-top:18px; padding:12px; background:#2563eb; color:#fff;
           border:0; border-radius:6px; font-size:16px; cursor:pointer; }
  #result { margin-top:16px; padding:12px; border-radius:6px; display:none; }
  .accepted { background:#dcfce7; color:#166534; }
  .duplicate { background:#fee2e2; color:#991b1b; }
  .invalid { background:#fee2e2; color:#991b1b; }
  .review { background:#fef9c3; color:#854d0e; }
</style>
</head>
<body>
<div class="card">
  <h2>تسجيل عميل جديد</h2>
  <label>الاسم</label>
  <input id="name" placeholder="مثال: أحمد حسن">
  <label>الإيميل</label>
  <input id="email" placeholder="example@gmail.com">
  <label>رقم الموبايل</label>
  <input id="phone" placeholder="01012345678">
  <button onclick="send()">تسجيل</button>
  <div id="result"></div>
</div>

<script>
async function send() {
  const body = {
    name: document.getElementById("name").value,
    email: document.getElementById("email").value,
    phone: document.getElementById("phone").value
  };
  const res = await fetch("/submit", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  });
  const data = await res.json();
  const box = document.getElementById("result");
  box.className = data.status;
  box.textContent = data.message;
  box.style.display = "block";
}
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return PAGE


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    status, message = process(
        data.get("name", ""), data.get("email", ""), data.get("phone", ""))
    return jsonify({"status": status, "message": message})


create_tables()

if __name__ == "__main__":
    app.run(port=5000)