# وظيفته: يولّد 130 عميل (أسماء وأرقام مصرية) ويحفظهم في customers.csv
# فيهم: 100 فريد + 20 مكرر + 6 غير صالح + 4 من عيلة بنفس التليفون
import csv
import random

random.seed(42)

first_names = ["Ahmed", "Mohamed", "Mahmoud", "Mostafa", "Omar", "Youssef", "Karim",
               "Ali", "Hassan", "Khaled", "Tarek", "Amr", "Hossam", "Ibrahim", "Sherif",
               "Sara", "Mona", "Nour", "Fatma", "Heba", "Salma", "Yasmin", "Aya",
               "Rania", "Dina", "Nada", "Mariam", "Hana", "Laila", "Esraa"]
last_names = ["Hassan", "Ali", "Ibrahim", "Mahmoud", "Abdelrahman", "Saleh", "Farouk",
              "Mansour", "Fathy", "Nasser", "Ezzat", "Shaker", "Salem", "Gaber",
              "Zaki", "Morsy", "Helmy", "Sabry", "Fouad", "Kamel"]
domains = ["gmail.com", "gmail.com", "gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
prefixes = ["010", "011", "012", "015"]

used_emails = set()
used_phones = set()

def make_person():
    while True:
        first = random.choice(first_names)
        last = random.choice(last_names)
        email = "{}.{}{}@{}".format(first.lower(), last.lower(),
                                    random.randint(1, 99), random.choice(domains))
        phone = random.choice(prefixes) + "".join(str(random.randint(0, 9)) for _ in range(8))
        if email not in used_emails and phone not in used_phones:
            used_emails.add(email)
            used_phones.add(phone)
            return {"full_name": first + " " + last, "email": email, "phone": phone}

records = []

# 1) 100 عميل فريد
for _ in range(100):
    records.append(make_person())

# 2) 10 مكررات تماماً
for rec in random.sample(records[:100], 10):
    records.append(dict(rec))

# 3) 10 مكررات بشكل مختلف (حروف كبيرة ومسافات)
for rec in random.sample(records[:100], 10):
    records.append({
        "full_name": "  " + rec["full_name"].upper() + " ",
        "email": " " + rec["email"].upper() + " ",
        "phone": rec["phone"],
    })

# 4) عيلة بنفس التليفون (False Positive)
for first in ["Mahmoud", "Mona", "Mostafa", "Menna"]:
    records.append({
        "full_name": first + " Elsayed",
        "email": first.lower() + ".elsayed@gmail.com",
        "phone": "01234567890",
    })

# 5) سجلات غير صالحة
for _ in range(5):
    p = make_person()
    p["email"] = p["email"].replace("@", "")
    records.append(p)
p = make_person()
p["full_name"] = ""
records.append(p)

random.shuffle(records)

with open("customers.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["full_name", "email", "phone"])
    writer.writeheader()
    writer.writerows(records)

print("Done! customers.csv created with", len(records), "records")