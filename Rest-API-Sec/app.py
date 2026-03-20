import os
from flask import Flask, request, jsonify
import psycopg2
from dotenv import load_dotenv
from functools import wraps

# =====================
# Load env
# =====================
load_dotenv()

app = Flask(__name__)

# =====================
# API Key Decorator
# =====================
API_KEY = os.getenv("API_KEY")

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('Authorization')
        if key != f"Bearer {API_KEY}":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# =====================
# Koneksi ke Neon
# =====================
conn = psycopg2.connect(
    host=os.getenv("NEON_HOSTNAME"),
    user=os.getenv("NEON_USER"),
    password=os.getenv("NEON_PASSWORD"),
    port=os.getenv("NEON_PORT"),
    dbname=os.getenv("NEON_DATABASE"),
    sslmode="require"
)

# =====================
# Inisialisasi tabel
# =====================
def init_db():
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)
        conn.commit()

init_db()

# =====================
# ROUTES CRUD
# =====================

# ----- GET all users -----
@app.route('/api/users', methods=['GET'])
@require_api_key
def get_users():
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, email FROM users ORDER BY id")
        rows = cur.fetchall()
        users = [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]
    return jsonify(users), 200

# ----- POST new user -----
@app.route('/api/users', methods=['POST'])
@require_api_key
def add_user():
    data = request.get_json()
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({"error": "name dan email wajib diisi"}), 400

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
                (data['name'], data['email'])
            )
            user_id = cur.fetchone()[0]
            conn.commit()
        return jsonify({"message": "user berhasil ditambahkan", "id": user_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400

# ----- PUT update user -----
@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_api_key
def update_user(user_id):
    data = request.get_json()
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({"error": "name dan email wajib diisi"}), 400

    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET name=%s, email=%s WHERE id=%s",
                (data['name'], data['email'], user_id)
            )
            if cur.rowcount == 0:
                return jsonify({"error": "User tidak ditemukan"}), 404
            conn.commit()
        return '', 204
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400

# ----- DELETE user -----
@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_api_key
def delete_user(user_id):
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
            if cur.rowcount == 0:
                return jsonify({"error": "User tidak ditemukan"}), 404
            conn.commit()
        return '', 204
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400

# =====================
# RUN APP
# =====================
if __name__ == '__main__':
    app.run(port=8080, debug=False)