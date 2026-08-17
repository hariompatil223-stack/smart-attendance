import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, jsonify

# Setup absolute paths to prevent TemplateNotFound errors on Linux hosting (Render)
base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

# Retrieve Database URL from Render Environment Variables
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Establishes connection to the Supabase PostgreSQL database."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """Initializes the students and attendance tables if they don't exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            qr_code_data TEXT UNIQUE NOT NULL
        );
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            student_id TEXT REFERENCES students(student_id),
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

# Initialize DB structures upon startup
init_db()

@app.route('/')
def index():
    """Render main scanning/mark page."""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Render attendance dashboard view."""
    return render_template('dashboard.html')

@app.route('/api/mark-attendance', methods=['POST'])
def mark_attendance():
    """API endpoint to record student attendance."""
    data = request.json
    qr_data = data.get('qr_data')
    lat = data.get('latitude')
    lon = data.get('longitude')

    if not qr_data:
        return jsonify({'status': 'error', 'message': 'Invalid QR Data'}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Check if student exists
    cur.execute('SELECT * FROM students WHERE qr_code_data = %s', (qr_data,))
    student = cur.fetchone()

    if not student:
        cur.close()
        conn.close()
        return jsonify({'status': 'error', 'message': 'Student not registered'}), 404

    # Record attendance entry
    cur.execute('''
        INSERT INTO attendance (student_id, name, status, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s)
    ''', (student['student_id'], student['name'], 'Present', lat, lon))
    
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'status': 'success', 'message': f"Attendance marked for {student['name']}"})

@app.route('/api/attendance-records', methods=['GET'])
def get_attendance():
    """API endpoint to fetch all attendance records for dashboard."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM attendance ORDER BY timestamp DESC')
    records = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(records)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
