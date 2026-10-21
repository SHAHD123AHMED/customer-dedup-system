# وظيفته: يدوّر على التكرار القديم اللي في جدول customers
#   python find_duplicates.py          -> يعرض التكرار بس (من غير ما يغيّر حاجة)
#   python find_duplicates.py --apply  -> ينقل التكرار لـ rejected_records ويشيله من customers
import os
import sys
import psycopg2


def get_db_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    with open("db_url.txt") as f:
        return f.read().strip()


apply_changes = "--apply" in sys.argv

conn = psycopg2.connect(get_db_url())
cur = conn.cursor()

# بندوّر بالتليفون وبالإيميل (بعد تحويله لحروف صغيرة)
checks = [("phone", "phone"), ("email", "LOWER(email)")]

to_remove = {}   # id -> (full_name, email, phone, السبب)

for label, expr in checks:
    cur.execute(
        "SELECT " + expr + ", COUNT(*) FROM customers "
        "GROUP BY " + expr + " HAVING COUNT(*) > 1")
    groups = cur.fetchall()
    print("Duplicate groups by %s: %d" % (label, len(groups)))

    for value, count in groups:
        cur.execute(
            "SELECT id, full_name, email, phone FROM customers "
            "WHERE " + expr + " = %s ORDER BY id", (value,))
        rows = cur.fetchall()
        keep = rows[0]                      # الأقدم هو اللي بيفضل
        print("  keep id=%s | %s | %s | %s" % keep)
        for r in rows[1:]:
            print("  dup  id=%s | %s | %s | %s" % r)
            to_remove[r[0]] = (r[1], r[2], r[3], "duplicate: found by cleanup (same %s)" % label)

print()
print("Total duplicate rows found:", len(to_remove))

if apply_changes and to_remove:
    for row_id, (name, email, phone, why) in to_remove.items():
        cur.execute(
            "INSERT INTO rejected_records (full_name, email, phone, reason) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (name, email, phone, why))
        cur.execute("DELETE FROM customers WHERE id = %s", (row_id,))
    conn.commit()
    print("Moved to rejected_records and removed from customers:", len(to_remove))
elif to_remove:
    print("Dry run only. Add --apply to move them.")

conn.close()