import requests
import bcrypt

SUPABASE_URL = "https://kaigmxalaksuasrqhkef.supabase.co/rest/v1/"
SUPABASE_KEY = "sb_publishable_v1Y2u_g4WmBMdMvjVvC_ig_90EDba5j"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

def seed():
    print("Seeding default data to Supabase database...")

    # 1. Seed Roles
    roles = [
        {"id": 1, "name": "Admin"},
        {"id": 2, "name": "HOD"},
        {"id": 3, "name": "AHOD"},
        {"id": 4, "name": "Staff"},
        {"id": 5, "name": "Student"},
        {"id": 6, "name": "CR"}
    ]
    print("Syncing roles...")
    res = requests.post(f"{SUPABASE_URL}roles", headers=headers, json=roles)
    if res.status_code in [200, 201]:
         print("  SUCCESS: Roles seeded.")
    else:
         print(f"  FAILED seeding roles: {res.status_code} - {res.text}")

    # 2. Seed Default Admin User
    admin_password = "admin123"
    admin_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin_user = {
        "id": "ADMIN01",
        "name": "System Administrator",
        "password_hash": admin_hash,
        "role_id": 1
    }
    print("Syncing Admin user 'ADMIN01' (Password: 'admin123')...")
    res = requests.post(f"{SUPABASE_URL}users", headers=headers, json=[admin_user])
    if res.status_code in [200, 201]:
         print("  SUCCESS: Admin user seeded.")
    else:
         print(f"  FAILED seeding admin user: {res.status_code} - {res.text}")

    # 3. Seed Default System Settings
    settings = [
        {"key": "academic_year", "value": "2025-2026"},
        {"key": "semester", "value": "Odd Semester (Semester I/III/V)"}
    ]
    print("Syncing system settings...")
    res = requests.post(f"{SUPABASE_URL}system_settings", headers=headers, json=settings)
    if res.status_code in [200, 201]:
         print("  SUCCESS: System settings seeded.")
    else:
         print(f"  FAILED seeding system settings: {res.status_code} - {res.text}")

    print("\nSupabase seeding complete! You can now login with:")
    print("  User ID: ADMIN01")
    print("  Password: admin123")
    print("  Role: Admin")

if __name__ == '__main__':
    seed()
