import os
import sqlite3

# Create static/proofs folder
if not os.path.exists("static/proofs"):
    os.makedirs("static/proofs")
    print("📁 Created static/proofs directory!")

# Add video_proof column to database
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE attendance_logs ADD COLUMN video_proof TEXT")
    conn.commit()
    print("✅ Added video_proof column to database!")
except sqlite3.OperationalError:
    print("⚠️ Column video_proof already exists.")

conn.close()