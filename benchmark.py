# وظيفته: يقيس الزمن قبل وبعد الـ Index، ويقارن طريقتين للمقارنة بالتشابه
#   python benchmark.py          -> 1000 صف (زي التاسك)
#   python benchmark.py 100000   -> داتا أكبر (الفرق بيبان أكتر)
# بيشتغل على جدول مؤقت bench_customers وبيمسحه في الآخر (مش بيلمس جداولك).
import os
import sys
import time
import psycopg2
from rapidfuzz import fuzz

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
LOOKUPS = 200


def get_db_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    with open("db_url.txt") as f:
        return f.read().strip()


conn = psycopg2.connect(get_db_url())
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS bench_customers")
cur.execute("""
    CREATE TABLE bench_customers (
        id SERIAL PRIMARY KEY, full_name TEXT, email TEXT, phone TEXT)
""")
cur.execute("""
    INSERT INTO bench_customers (full_name, email, phone)
    SELECT 'user ' || g, 'user' || g || '@test.com', '01' || lpad(g::text, 9, '0')
    FROM generate_series(1, %s) AS g
""", (N,))
cur.execute("ANALYZE bench_customers")
conn.commit()

ids = [(i * 37) % N + 1 for i in range(LOOKUPS)]
phones = ["01" + str(i).zfill(9) for i in ids]


def lookups_ms():
    start = time.perf_counter()
    for p in phones:
        cur.execute("SELECT id FROM bench_customers WHERE phone = %s", (p,))
        cur.fetchone()
    return (time.perf_counter() - start) * 1000


def server_ms():
    cur.execute("EXPLAIN ANALYZE SELECT id FROM bench_customers WHERE phone = %s", (phones[0],))
    for (line,) in cur.fetchall():
        if "Execution Time" in line:
            return float(line.split(":")[1].replace("ms", "").strip())
    return None


lookups_ms()                       # تسخين الاتصال
before_total = lookups_ms()
before_server = server_ms()

cur.execute("CREATE INDEX idx_bench_phone ON bench_customers (phone)")
cur.execute("ANALYZE bench_customers")
conn.commit()

after_total = lookups_ms()
after_server = server_ms()

# مقارنة التشابه: كل الجدول ضد المرشحين بس
new_names = ["user %d" % i for i in ids[:20]]
new_phones = phones[:20]

start = time.perf_counter()
cur.execute("SELECT full_name FROM bench_customers")
all_names = [r[0] for r in cur.fetchall()]
for nm in new_names:
    max(fuzz.ratio(nm, other) for other in all_names)
naive_ms = (time.perf_counter() - start) * 1000

start = time.perf_counter()
for nm, ph in zip(new_names, new_phones):
    cur.execute("SELECT full_name FROM bench_customers WHERE phone = %s", (ph,))
    cands = [r[0] for r in cur.fetchall()]
    if cands:
        max(fuzz.ratio(nm, c) for c in cands)
cand_ms = (time.perf_counter() - start) * 1000

cur.execute("DROP TABLE bench_customers")
conn.commit()
conn.close()

lines = [
    "Rows in test table: %d" % N,
    "",
    "[1] %d lookups by phone (total time incl. network)" % LOOKUPS,
    "    before index: %.1f ms" % before_total,
    "    after  index: %.1f ms" % after_total,
    "",
    "[2] One query, server-side time (EXPLAIN ANALYZE)",
    "    before index: %s ms" % before_server,
    "    after  index: %s ms" % after_server,
    "",
    "[3] Fuzzy comparison for 20 new rows",
    "    against ALL rows        : %.1f ms" % naive_ms,
    "    against candidates only : %.1f ms" % cand_ms,
]
print("\n".join(lines))
with open("benchmark_results.txt", "w", encoding="utf-8") as out:
    out.write("\n".join(lines) + "\n")
print("\nSaved to benchmark_results.txt")