import sqlite3
import os
import requests
import json

SUPABASE_URL = "https://kaigmxalaksuasrqhkef.supabase.co/rest/v1/"
SUPABASE_KEY = "sb_publishable_v1Y2u_g4WmBMdMvjVvC_ig_90EDba5j"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

# Tables list in dependency order (so foreign keys don't fail)
tables = [
    "roles",
    "users",
    "departments",
    "courses",
    "classes",
    "subjects",
    "staff",
    "students",
    "staff_subject_assignments",
    "attendance",
    "staff_attendance",
    "class_representatives",
    "announcements",
    "leave_applications",
    "timetables",
    "system_settings"
]

def sync():
    db_path = "instance/unilog.db"
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} does not exist!")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Starting synchronization of SQLite tables to Supabase...")

    for table in tables:
        print(f"Syncing table '{table}'...")
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            if not rows:
                print(f"  Table is empty, skipping.")
                continue

            payload = []
            for row in rows:
                payload.append(dict(row))

            # Send payload via POST using PostgREST upsert headers
            res = requests.post(f"{SUPABASE_URL}{table}", headers=headers, json=payload, timeout=15)
            if res.status_code in [200, 201]:
                print(f"  SUCCESS: Uploaded {len(rows)} rows.")
            else:
                print(f"  FAILED: Status {res.status_code} - {res.text}")
        except Exception as e:
            print(f"  ERROR syncing table '{table}': {e}")

    conn.close()
    print("\nSync completed successfully!")

if __name__ == '__main__':
    sync()
