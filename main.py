# وظيفته: الحارس لملفات CSV. يقرأ الملف، يمرر كل سجل على dedup.process_record،
# ويطبع ملخص. (قواعد التصنيف نفسها في dedup.py)
# التشغيل العادي: بياخد customers.csv
# أو تكتب اسم ملف تاني: python main.py new_batch.csv
import csv
import os
import sys
import psycopg2
from dedup import ensure_tables, process_record


def get_db_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    with open("db_url.txt") as f:
        return f.read().strip()


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "customers.csv"

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor()
    ensure_tables(cur)
    conn.commit()

    counts = {"accepted": 0, "duplicate": 0, "invalid": 0, "review": 0}
    total = 0

    with open(input_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            status, _ = process_record(
                cur, row["full_name"], row["email"], row["phone"])
            counts[status] += 1

    conn.commit()

    print("File      :", input_file)
    print("Total     :", total)
    print("Accepted  :", counts["accepted"])
    print("Duplicates:", counts["duplicate"])
    print("Invalid   :", counts["invalid"])
    print("Review    :", counts["review"])
    print()
    print("--- Rows now in CLOUD database ---")
    for table in ["customers", "rejected_records", "review_queue"]:
        cur.execute("SELECT COUNT(*) FROM " + table)
        print(table, ":", cur.fetchone()[0])

    conn.close()
