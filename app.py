from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import math
import base64
import time
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Fetch database connection string from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:[#Hariom8226]@db.nqfznhgfwgydwphpqfqh.supabase.co:5432/postgres")

CLASSROOM_LAT = 18.6493
CLASSROOM_LON = 73.7639
ALLOWED_RADIUS_METERS = 50.0

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    if not os.path.exists("static/proofs"):
        os.makedirs("static/proofs")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            qr_token VARCHAR(255) UNIQUE NOT NULL
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_logs (
            log_id SERIAL PRIMARY KEY,
            student_id VARCHAR(50) REFERENCES students(student_id),
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            video_proof TEXT
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/proofs/<filename>')
def serve_proof(filename):
    return send_from_directory('static/proofs', filename)

@app.route('/api/mark-attendance', methods=['POST'])
def mark_attendance():
    data = request.get_json()
    qr_token = data.get('qr_token')
    user_lat = data.get('latitude')
    user_lon = data.get('longitude')
    video_base64 = data.get('video')

    if not qr_token:
        return jsonify({"status": "error", "message": "❌ Invalid QR Code!"}), 400

    if user_lat is None or user_lon is None:
        return jsonify({"status": "error", "message": "📍 Location required!"}), 400

    distance = haversine_distance(CLASSROOM_LAT, CLASSROOM_LON, float(user_lat), float(user_lon))
    if distance > ALLOWED_RADIUS_METERS:
        return jsonify({"status": "error", "message": f"❌ Out of bounds ({int(distance)}m away)!"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT student_id, name FROM students WHERE qr_token = %s", (qr_token,))
    student = cursor.fetchone()

    if not student:
        cursor.close()
        conn.close()
        return jsonify({"status": "error", "message": "⚠️ QR Code Not Registered!"}), 404

    student_id = student['student_id']
    name = student['name']

    cursor.execute("""
        SELECT log_id FROM attendance_logs 
        WHERE student_id = %s AND DATE(scanned_at) = CURRENT_DATE
    """, (student_id,))
    already_scanned = cursor.fetchone()

    if already_scanned:
        cursor.close()
        conn.close()
        return jsonify({"status": "warning", "message": f"⚠️ {name} is already marked present today!"})

    video_filename = None
    if video_base64:
        try:
            video_filename = f"{student_id}_{int(time.time())}.webm"
            filepath = os.path.join("static/proofs", video_filename)
            video_bytes = base64.b64decode(video_base64.split(',')[1])
            with open(filepath, "wb") as f:
                f.write(video_bytes)
        except Exception as e:
            print("Error saving video:", e)

    cursor.execute("""
        INSERT INTO attendance_logs (student_id, latitude, longitude, video_proof) 
        VALUES (%s, %s, %s, %s)
    """, (student_id, user_lat, user_lon, video_filename))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "success", "message": f"✅ Verified & Marked Present: {name}"})

@app.route('/api/dashboard-data', methods=['GET'])
def get_dashboard_data():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT student_id, name, qr_token FROM students")
    all_students = cursor.fetchall()

    cursor.execute("""
        SELECT student_id, scanned_at, latitude, longitude, video_proof 
        FROM attendance_logs 
        WHERE DATE(scanned_at) = CURRENT_DATE
    """)
    logs = cursor.fetchall()

    present_dict = {row['student_id']: row for row in logs}

    student_list = []
    for s in all_students:
        s_id = s['student_id']
        is_present = s_id in present_dict
        student_list.append({
            "student_id": s_id,
            "name": s['name'],
            "email": s['qr_token'],
            "status": "Present" if is_present else "Absent",
            "proof": present_dict.get(s_id, {}) if is_present else None
        })

    cursor.close()
    conn.close()

    return jsonify({
        "status": "success",
        "total": len(all_students),
        "present_count": len(present_dict),
        "absent_count": len(all_students) - len(present_dict),
        "students": student_list
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)