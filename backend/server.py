from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os, threading, webbrowser, json
from datetime import datetime

# MongoDB
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from blockchain_file_integrity import Blockchain, FileIntegrityManager

app = Flask(__name__, static_folder="../frontend")
CORS(app)

BASE = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
USERS_FILE = os.path.join(BASE, "users.json")

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump([
            {"username":"admin","password":"admin123"},
            {"username":"user1","password":"password1"},
            {"username":"user2","password":"password2"},
        ], f, indent=2)

# ---- Mongo configuration (use env vars in production) ----
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "blockchain_app")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
users_col = db.get_collection("users")
files_col = db.get_collection("files")

# If there's an existing users.json file, migrate accounts to MongoDB (only when collection empty)
try:
    if os.path.exists(USERS_FILE) and users_col.count_documents({}) == 0:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            current_users = json.load(f)
        migrated = 0
        for u in current_users:
            username = u.get("username")
            password = u.get("password")
            if username and password and not users_col.find_one({"username": username}):
                users_col.insert_one({
                    "username": username,
                    "password": generate_password_hash(password)
                })
                migrated += 1
        if migrated:
            print(f"[📦] Migrated {migrated} users from users.json to MongoDB ({MONGO_DB}.users)")
except Exception as _e:
    print("[⚠️] MongoDB migration skipped or failed:", _e)

blockchain = Blockchain()
if not blockchain.load_chain():
    blockchain.create_genesis_block()
    blockchain.save_chain()
file_manager = FileIntegrityManager(blockchain)

@app.route("/")
def serve_login():
    return send_from_directory("../frontend", "login.html")

@app.route("/<path:p>")
def static_files(p):
    return send_from_directory("../frontend", p)

@app.route("/api/login_user", methods=["POST"])
def login_user():
    try:
        data = request.get_json(force=True)
        u, pw = (data.get("username"," ").strip(), data.get("password"," ").strip())

        # Try MongoDB first
        user_doc = users_col.find_one({"username": u})
        if user_doc:
            stored = user_doc.get("password", "")
            # support old-migration where password may be stored unhashed by mistake
            if check_password_hash(stored, pw) or stored == pw:
                # if stored was plaintext, rehash and update
                if stored == pw:
                    users_col.update_one({"username": u}, {"$set": {"password": generate_password_hash(pw)}})
                return jsonify({"success": True, "message": "✅ Login successful!"})
            else:
                return jsonify({"success": False, "message": "❌ Invalid username or password."})

        # Fallback to file-based users.json if not found in DB (keeps backward compatibility)
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        ok = any(x["username"] == u and x["password"] == pw for x in users)
        return jsonify({"success": ok, "message": "✅ Login successful!" if ok else "❌ Invalid username or password."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/register_user", methods=["POST"])
def register_user():
    try:
        data = request.get_json(force=True)
        u, pw = (data.get("username","" ).strip(), data.get("password","" ).strip())
        if not u or not pw:
            return jsonify({"success": False, "message":"⚠️ Username and password are required."})

        # Check DB for existing user
        if users_col.find_one({"username": u}):
            return jsonify({"success": False, "message":"⚠️ Username already exists."})

        # Also check users.json for compatibility (if present)
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    users = json.load(f)
                if any(x["username"] == u for x in users):
                    return jsonify({"success": False, "message": "⚠️ Username already exists."})
        except Exception:
            pass

        # Store hashed password in MongoDB
        users_col.insert_one({"username": u, "password": generate_password_hash(pw), "created_at": datetime.now().isoformat()})
        return jsonify({"success": True, "message":"✅ Registration successful!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/register", methods=["POST"])
def register_file():
    try:
        f = request.files["file"]
        uploader_id = request.form.get("uploader_id","anonymous").strip()
        path = os.path.join(UPLOAD_FOLDER, f.filename)
        f.save(path)
        ok = file_manager.register_file(path, uploader_id, "FILE_REGISTERED")
        blockchain.save_chain()

        # store metadata in MongoDB (if available)
        try:
            file_hash = file_manager.get_file_hash(path)
            metadata = file_manager.get_file_metadata(path) or {}
            files_col.insert_one({
                "filename": f.filename,
                "filepath": path,
                "uploader_id": uploader_id,
                "action": "FILE_REGISTERED",
                "file_hash": file_hash,
                "file_size": metadata.get("size"),
                "registered_at": datetime.now().isoformat()
            })
        except Exception as _e:
            print("[⚠️] Storing file metadata in MongoDB failed:", _e)

        return jsonify({"success": ok, "message": f"✅ {f.filename} registered successfully!" if ok else "❌ Registration failed."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/verify", methods=["POST"])
def verify_file():
    try:
        f = request.files["file"]
        path = os.path.join(UPLOAD_FOLDER, f.filename)
        f.save(path)
        ok = file_manager.verify_file_integrity(path)
        return jsonify({"success": ok, "message": f"✅ {f.filename} integrity verified." if ok else f"❌ {f.filename} appears tampered or unregistered."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/validate", methods=["GET"])
def validate_chain():
    ok = blockchain.is_valid()
    return jsonify({"success": ok, "message":"✅ Blockchain valid — no corruption found." if ok else "❌ Blockchain corrupted!"})

@app.route("/history", methods=["GET"])
def history_all():
    try:
        with open(os.path.join(BASE,"blockchain_data.json"),"r") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# SINGLE, correct user-history route
@app.route("/api/history_user", methods=["GET"])
def history_user():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "message":"Username required"}), 400
    blocks = []
    for b in blockchain.chain:
        d = b.data if isinstance(b.data, dict) else {}
        if d.get("uploader_id") == username:
            blocks.append({
                "index": b.index,
                "filename": d.get("filename"),
                "action": d.get("action"),
                "file_hash": d.get("file_hash"),
                "file_size": d.get("file_size"),
                "timestamp": b.timestamp
            })
    return jsonify({"success": True, "count": len(blocks), "blocks": blocks})

@app.route("/demo", methods=["GET"])
def demo():
    return jsonify({"message":"🎬 Demo running successfully — blockchain operational."})

def open_frontend():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1.0, open_frontend).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
