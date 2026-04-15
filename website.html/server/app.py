from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ─────────────────────────────────────────
# DB connection
# ─────────────────────────────────────────
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="divya@4257",
    database="PLANNERIA"
)

def get_cursor():
    """Return a fresh dictionary cursor, reconnecting if the connection dropped."""
    db.ping(reconnect=True, attempts=3, delay=2)
    return db.cursor(dictionary=True)

# ─────────────────────────────────────────
# Home
# ─────────────────────────────────────────
@app.route('/')
def home():
    return "Planneria Backend Running 🚀"


# ─────────────────────────────────────────
# SIGNUP  ← NEW
# ─────────────────────────────────────────
@app.route('/signup', methods=['POST'])
def signup():
    """
    Register a new user.
    Expects JSON: { name, email, password }
    Validates: all fields required, email must be unique.
    Returns user_id on success so the frontend can auto-login.
    """
    data = request.json

    name     = (data.get('name')     or '').strip()
    email    = (data.get('email')    or '').strip()
    password = (data.get('password') or '').strip()

    # Validate required fields
    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    # Check email uniqueness
    cursor = get_cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({"error": "Email already registered. Please login."}), 409

    # Insert new user
    ins_cursor = db.cursor()
    ins_cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
        (name, email, password)
    )
    db.commit()
    new_id = ins_cursor.lastrowid

    return jsonify({
        "message": "User created",
        "success": True,
        "user_id": new_id,
        "name": name
    }), 201


# ─────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    """
    Authenticate a user.
    Expects JSON: { email, password }
    Returns user_id + name on success.
    """
    data = request.json
    email    = (data.get('email')    or '').strip()
    password = (data.get('password') or '').strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    cursor = get_cursor()
    cursor.execute(
        "SELECT id, name FROM users WHERE email = %s AND password = %s",
        (email, password)
    )
    user = cursor.fetchone()

    if user:
        return jsonify({
            "message": "Login successful",
            "user_id": user['id'],
            "name":    user['name']
        })
    return jsonify({"error": "Invalid email or password"}), 401


# ─────────────────────────────────────────
# Users (admin / utility)
# ─────────────────────────────────────────
@app.route('/users', methods=['GET'])
def get_users():
    cursor = get_cursor()
    cursor.execute("SELECT id, name, email FROM users")   # never return passwords
    return jsonify(cursor.fetchall())


# ─────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────
@app.route('/tasks/<int:user_id>', methods=['GET'])
def get_tasks(user_id):
    cursor = get_cursor()
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s", (user_id,))
    return jsonify(cursor.fetchall())

@app.route('/add_task', methods=['POST'])
def add_task():
    cursor = db.cursor()
    data = request.json
    cursor.execute(
        "INSERT INTO tasks (user_id, task, status) VALUES (%s, %s, %s)",
        (data['user_id'], data['task'], data['status'])
    )
    db.commit()
    return jsonify({"message": "Task added successfully"})

@app.route('/delete_task/<int:id>', methods=['DELETE'])
def delete_task(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (id,))
    db.commit()
    return jsonify({"message": "Task deleted successfully"})

@app.route('/update_task/<int:id>', methods=['PUT'])
def update_task(id):
    cursor = db.cursor()
    data = request.json
    cursor.execute(
        "UPDATE tasks SET status = %s WHERE id = %s",
        (data.get('status'), id)
    )
    db.commit()
    return jsonify({"message": "Task updated successfully"})


# ─────────────────────────────────────────
# Notes
# ─────────────────────────────────────────
@app.route('/notes/<int:user_id>', methods=['GET'])
def get_notes(user_id):
    cursor = get_cursor()
    cursor.execute("SELECT * FROM notes WHERE user_id = %s", (user_id,))
    return jsonify(cursor.fetchall())

@app.route('/add_note', methods=['POST'])
def add_note():
    cursor = db.cursor()
    data = request.json
    cursor.execute(
        "INSERT INTO notes (user_id, title, content) VALUES (%s, %s, %s)",
        (data['user_id'], data['title'], data['content'])
    )
    db.commit()
    return jsonify({"message": "Note added successfully"})

@app.route('/delete_note/<int:id>', methods=['DELETE'])
def delete_note(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM notes WHERE id = %s", (id,))
    db.commit()
    return jsonify({"message": "Note deleted successfully"})


# ─────────────────────────────────────────
# Goals
# ─────────────────────────────────────────
@app.route('/goals', methods=['GET'])
def get_goals():
    cursor = get_cursor()
    cursor.execute("SELECT * FROM goals")
    return jsonify(cursor.fetchall())


# ─────────────────────────────────────────
# Timetable — CRUD
# ─────────────────────────────────────────
@app.route('/timetable/<int:user_id>', methods=['GET'])
def get_timetable(user_id):
    cursor = get_cursor()
    cursor.execute("SELECT * FROM timetable WHERE user_id = %s", (user_id,))
    return jsonify(cursor.fetchall())


@app.route('/add_timetable', methods=['POST'])
def add_timetable():
    """
    Insert or update a timetable entry.
    ON DUPLICATE KEY UPDATE prevents duplicate-key errors when re-saving a cell.
    Expects JSON: { user_id, day, time, subject }
    """
    cursor = db.cursor()
    data   = request.json

    for field in ['user_id', 'day', 'time', 'subject']:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400

    cursor.execute(
        """
        INSERT INTO timetable (user_id, day, time, subject)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE subject = VALUES(subject)
        """,
        (data['user_id'], data['day'].strip(), data['time'].strip(), data['subject'].strip())
    )
    db.commit()
    return jsonify({"message": "Timetable entry saved successfully"})


@app.route('/update_timetable', methods=['PUT'])
def update_timetable():
    """
    Update an existing entry by (user_id, day, time).
    Expects JSON: { user_id, day, time, subject }
    """
    cursor = db.cursor()
    data   = request.json

    for field in ['user_id', 'day', 'time', 'subject']:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400

    cursor.execute(
        """
        UPDATE timetable
        SET subject = %s
        WHERE user_id = %s AND day = %s AND time = %s
        """,
        (data['subject'].strip(), data['user_id'], data['day'].strip(), data['time'].strip())
    )
    db.commit()
    return jsonify({"message": "Timetable entry updated successfully"})


@app.route('/delete_timetable_entry', methods=['DELETE'])
def delete_timetable_entry():
    """
    Delete a single cell by (user_id, day, time).
    Expects JSON: { user_id, day, time }
    """
    cursor  = db.cursor()
    data    = request.json

    user_id = data.get('user_id')
    day     = data.get('day')
    time    = data.get('time')

    if not user_id or not day or not time:
        return jsonify({"error": "Missing data (need user_id, day, time)"}), 400

    cursor.execute(
        "DELETE FROM timetable WHERE user_id = %s AND day = %s AND time = %s",
        (user_id, day, time)
    )
    db.commit()
    return jsonify({"message": "Entry deleted successfully"})


@app.route('/delete_timetable/<int:user_id>', methods=['DELETE'])
def delete_timetable(user_id):
    """Delete ALL timetable entries for a user."""
    cursor = db.cursor()
    cursor.execute("DELETE FROM timetable WHERE user_id = %s", (user_id,))
    db.commit()
    return jsonify({"message": "Timetable cleared successfully"})


# ─────────────────────────────────────────
# DATABASE VIEWS  ← NEW (required by faculty)
# ─────────────────────────────────────────

@app.route('/get_timetable_view', methods=['GET'])
def get_timetable_view():
    """
    Reads from the SQL VIEW: user_timetable_view
    Returns: [ { name, day, subject, time }, ... ]
    """
    cursor = get_cursor()
    cursor.execute("SELECT * FROM user_timetable_view")
    return jsonify(cursor.fetchall())


@app.route('/get_summary', methods=['GET'])
def get_summary():
    """
    Reads from the SQL VIEW: user_summary_view
    Returns: [ { name, total_entries }, ... ]
    """
    cursor = get_cursor()
    cursor.execute("SELECT * FROM user_summary_view")
    return jsonify(cursor.fetchall())


# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)