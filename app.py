# وظيفته: صفحة ويب فيها فورم تسجيل عميل + خدمة بترد فوراً.
# بيستخدم نفس منطق dedup.py اللي بيستخدمه main.py.
import os
import psycopg2
from flask import Flask, request, jsonify
from dedup import ensure_tables, process_record

app = Flask(__name__)

DB_URL = os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")  # على السحابة
if not DB_URL:                                                       # على جهازك
    with open("db_url.txt") as f:
        DB_URL = f.read().strip()

MESSAGES = {
    "accepted": "تم التسجيل بنجاح. أهلاً بيك!",
    "duplicate": "البيانات دي مسجّلة عندنا قبل كده.",
    "invalid": "البيانات غير صحيحة: اكتب الاسم وإيميل صحيح وموبايل مصري من 11 رقم.",
    "review": "فيه تشابه مع بيانات مسجّلة. هنراجع بياناتك ونرد عليك.",
}


def get_connection():
    return psycopg2.connect(DB_URL)


def process(name, email, phone):
    conn = get_connection()
    cur = conn.cursor()
    try:
        status, _ = process_record(cur, name, email, phone)
        conn.commit()
        return status, MESSAGES[status]
    finally:
        conn.close()


def create_tables():
    conn = get_connection()
    cur = conn.cursor()
    ensure_tables(cur)
    conn.commit()
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
    data = request.get_json(silent=True) or {}
    status, message = process(
        data.get("name", ""), data.get("email", ""), data.get("phone", ""))
    return jsonify({"status": status, "message": message})


create_tables()

if __name__ == "__main__":
    app.run(port=5000)
