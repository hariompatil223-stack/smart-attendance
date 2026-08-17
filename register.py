import psycopg2

# ==============================================================================
# ⚙️ CONFIGURATION
# Replace YOUR_ACTUAL_PASSWORD with your Supabase database password.
# If your password has special characters (@, #, $, %), encode them:
# @ -> %40  |  # -> %23  |  $ -> %24  |  : -> %3A
# ==============================================================================
DATABASE_URL = "postgresql://postgres.nqfznhgfwgydwphpqfqh:%23Hariom8226@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

def register_students():
    conn = None
    cursor = None
    try:
        print("⚡ Connecting to Supabase Cloud Database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # 1. Ensure the students table exists in the cloud database
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                qr_token VARCHAR(255) UNIQUE NOT NULL
            );
        """)

        # 2. Define student records to insert: (Student_ID, Full_Name, QR_Token/Email)
        students_list = [
            ("STU101", "Hariom Patil", "hariom@gmail.com"),
            ("STU102", "Rahul Sharma", "rahul.sharma@gmail.com"),
            ("STU103", "Ananya Verma", "ananya.verma@gmail.com")
        ]

        # 3. Insert student records safely without duplicates
        for student_id, name, qr_token in students_list:
            cursor.execute("""
                INSERT INTO students (student_id, name, qr_token)
                VALUES (%s, %s, %s)
                ON CONFLICT (student_id) DO NOTHING;
            """, (student_id, name, qr_token))
            print(f"  Registered: {name} ({student_id})")

        conn.commit()
        print("\n🎉 All students successfully registered in the cloud database!")

    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    register_students()