import os
import datetime
import jwt
from flask import Flask, request, jsonify
import psycopg2
from dotenv import load_dotenv
from functools import wraps

# =====================
# Load env
# =====================
load_dotenv()
app = Flask(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY tidak ditemukan di .env")

# =====================
# JWT Decorator
# =====================
def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"error": "Token missing"}), 401

        try:
            token = auth.split(" ")[1]
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except Exception:
            return jsonify({"error": "Token invalid"}), 401

        return f(*args, **kwargs)
    return decorated

# =====================
# Login
# =====================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()

    if data.get("username") == "admin" and data.get("password") == "123":
        token = jwt.encode({
            "user": "admin",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, SECRET_KEY, algorithm="HS256")

        return jsonify({"token": token})

    return jsonify({"error": "Login gagal"}), 401

# =====================
# Koneksi DB Neon
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
# Init tabel
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
# CRUD (JWT Protected)
# =====================
@app.route('/api/users', methods=['GET'])
@require_token
def get_users():
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, email FROM users ORDER BY id")
        rows = cur.fetchall()
        users = [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
@require_token
def add_user():
    data = request.get_json()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            (data['name'], data['email'])
        )
        conn.commit()
    return '', 201

@app.route('/api/users/<int:id>', methods=['PUT'])
@require_token
def update_user(id):
    data = request.get_json()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET name=%s, email=%s WHERE id=%s",
            (data['name'], data['email'], id)
        )
        conn.commit()
    return '', 204

@app.route('/api/users/<int:id>', methods=['DELETE'])
@require_token
def delete_user(id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id=%s", (id,))
        conn.commit()
    return '', 204

# =====================
# Run
# =====================
if __name__ == '__main__':
    app.run(port=8080, debug=False)