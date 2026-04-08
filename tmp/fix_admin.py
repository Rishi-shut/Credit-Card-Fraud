import sqlite3
import os

db_path = 'fraud_detection.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Correct the Google email ID and the typo placeholder
    emails = ['mriganksingh7890@gmail.com', 'user_via_clerk@example.com']
    for email in emails:
        cur.execute("UPDATE users SET is_admin=1, dev_status='approved' WHERE email=?", (email,))
        print(f"Updated {email}: {cur.rowcount} rows")
    conn.commit()
    conn.close()
else:
    print("Database not found!")
