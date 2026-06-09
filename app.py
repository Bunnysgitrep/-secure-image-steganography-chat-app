from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import sqlite3
import os
import io
import base64
import hashlib
from PIL import Image
from cryptography.fernet import Fernet
# ================= ENCRYPTION =================

def generate_key(password):
    return base64.urlsafe_b64encode(
        hashlib.sha256(password.encode()).digest()
    )

def encrypt_message(message, password):
    fernet = Fernet(generate_key(password))
    return fernet.encrypt(message.encode()).decode()

def decrypt_message(encrypted_text, password):
    fernet = Fernet(generate_key(password))
    return fernet.decrypt(encrypted_text.encode()).decode()


# ================= STEGANOGRAPHY =================

def text_to_binary(text):
    return ''.join(format(ord(c), '08b') for c in text)

def binary_to_text(binary_data):
    chars = [binary_data[i:i+8] for i in range(0, len(binary_data), 8)]
    return ''.join(chr(int(c, 2)) for c in chars)

def encode_image(image, secret_data):

    binary_data = text_to_binary(secret_data) + "1111111111111110"
    pixels = image.load()

    data_index = 0

    for y in range(image.height):
        for x in range(image.width):

            if data_index >= len(binary_data):
                return image

            r, g, b = pixels[x, y]
            r = (r & ~1) | int(binary_data[data_index])
            pixels[x, y] = (r, g, b)

            data_index += 1

    return image


def decode_image(image):
    pixels = image.load()
    binary_data = ""

    for y in range(image.height):
        for x in range(image.width):

            r, g, b = pixels[x, y]
            binary_data += str(r & 1)

            if binary_data.endswith("1111111111111110"):
                binary_data = binary_data[:-16]
                return binary_to_text(binary_data)

    return None

app = Flask(__name__)
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        message TEXT,
        type TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()


# ================= MAIN PAGES =================

@app.route("/")
def home_page():
    return render_template("index.html")

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/register-page")
def register_page():
    return render_template("register.html")

@app.route("/chat-page")
def chat_page():
    return render_template("chat.html")

@app.route("/encode-page")
def encode_page():
    return render_template("encode.html")

@app.route("/decode-page")
def decode_page():
    return render_template("decode.html")

@app.route("/how-page")
def how_page():
    return render_template("how.html")

@app.route("/security-page")
def security_page():
    return render_template("security.html")



# ================= START =================
@app.route("/decode", methods=["POST"])
def decode():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        image_file = request.files["image"]
        password = request.form.get("password")

        if not password:
            return jsonify({"error": "Password required"}), 400

        # 🔥 Open image safely
        image = Image.open(image_file).convert("RGB")

        # Extract hidden data
        extracted = decode_image(image)

        if not extracted:
            return jsonify({"error": "No hidden message found"}), 400

        try:
            # 🔐 decrypt
            message = decrypt_message(extracted, password)
        except Exception:
            return jsonify({"error": "Wrong password"}), 401

        return jsonify({"message": message})

    except Exception as e:
        print("DECODE ERROR:", str(e))  # 👈 DEBUG
        return jsonify({"error": "Server error during decode"}), 500
       
@app.route("/encode", methods=["POST"])
def encode():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        image_file = request.files["image"]
        message = request.form.get("message")
        password = request.form.get("password")

        if not message or not password:
            return jsonify({"error": "Message & password required"}), 400

        image = Image.open(image_file).convert("RGB")

        encrypted = encrypt_message(message, password)
        encoded_img = encode_image(image, encrypted)

        buffer = io.BytesIO()
        encoded_img.save(buffer, format="PNG")  # 🔥 MUST BE PNG
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype="image/png",
            as_attachment=True,
            download_name="encoded_image.png"
        )

    except Exception as e:
        print("ENCODE ERROR:", str(e))
        return jsonify({"error": "Server error during encode"}), 500
    
# ================= AUTH =================

@app.route("/register", methods=["POST"])
def register():

    data = request.json

    # ✅ corrected names from frontend
    full_name = data["fullName"]
    username = data["username"].strip()
    password = generate_password_hash(data["password"])

    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        # ✅ check existing username
        cursor.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return jsonify({
                "error": "User already exists"
            }), 400

        # ✅ insert user
        cursor.execute(
            "INSERT INTO users(full_name, username, password) VALUES(?,?,?)",
            (full_name, username, password)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Registered successfully"
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"]
    password = data["password"]

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user[0], password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login success"})

@app.route("/check-user/<username>")
def check_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    conn.close()
    return jsonify({"exists": bool(user)})

@app.route("/view-users")
def view_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users")
    users = cursor.fetchall()
    conn.close()
    return jsonify(users)

# ================= IMAGE =================


@app.route("/upload-image", methods=["POST"])
def upload_image():
    file = request.files["image"]

    # 🔥 FORCE PNG FORMAT
    image = Image.open(file).convert("RGB")

    filename = "img_" + str(os.urandom(8).hex()) + ".png"
    path = os.path.join(UPLOAD_FOLDER, filename)

    # ✅ SAVE WITHOUT COMPRESSION LOSS
    image.save(path, format="PNG")

    return jsonify({
        "url": f"http://127.0.0.1:5000/uploads/{filename}"
    })

@app.route("/uploads/<filename>")
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ================= SOCKET =================
@socketio.on("join_room")
def join(data):
    room = "_".join(sorted([data["sender"], data["receiver"]]))
    join_room(room)

@socketio.on("send_message")
def send_message(data):
    sender = data["sender"]
    receiver = data["receiver"]
    message = data["message"]
    msg_type = data["type"]

    room = "_".join(sorted([sender, receiver]))

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages(sender,receiver,message,type) VALUES(?,?,?,?)",
                   (sender, receiver, message, msg_type))
    conn.commit()
    conn.close()

    emit("receive_message", {
        "sender": sender,
        "receiver": receiver,
        "message": message,
        "type": msg_type
    }, room=room)

@app.route("/get-messages/<u1>/<u2>")
def get_messages(u1, u2):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
    SELECT sender,message,type FROM messages
    WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
    ORDER BY timestamp
    """, (u1, u2, u2, u1))
    rows = cursor.fetchall()
    conn.close()

    return jsonify([{"sender":r[0],"message":r[1],"type":r[2]} for r in rows])
@app.route("/get-user-chats/<username>")
def get_user_chats(username):

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT DISTINCT
        CASE
            WHEN sender=? THEN receiver
            ELSE sender
        END as chat_user
    FROM messages
    WHERE sender=? OR receiver=?
    """,(username,username,username))

    rows = cursor.fetchall()
    conn.close()

    users = [r[0] for r in rows]

    return jsonify(users)

# ================= START =================
if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)