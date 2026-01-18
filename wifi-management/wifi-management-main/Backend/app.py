from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS
import os
import socket

# ✅ Import DB collections (ONLY from db.py)
from db import users_collection, admins_collection, sessions_collection

# ✅ Import Blueprints
from admin_routes import admin_routes
from auth_routes import auth_routes

# --------------------------------------------------
# ✅ APP CONFIG
# --------------------------------------------------
app = Flask(__name__)
CORS(app)

app.config["SECRET_KEY"] = "your-secret-key"

# --------------------------------------------------
# ✅ PATH CONFIG
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "Frontend")

# --------------------------------------------------
# ✅ REGISTER BLUEPRINTS
# --------------------------------------------------
app.register_blueprint(auth_routes, url_prefix="/api/auth")
app.register_blueprint(admin_routes, url_prefix="/api")  # Routes already have /admin prefix

# --------------------------------------------------
# ✅ ALLOW ONLY LOCAL NETWORK (Wi-Fi)
# --------------------------------------------------
@app.before_request
def allow_lan_only():
    ip = request.remote_addr

    # Allow localhost for testing
    if ip in ("127.0.0.1", "::1"):
        return

    # Allow private IP ranges only
    if not (
        ip.startswith("192.168.") or
        ip.startswith("10.") or
        ip.startswith("172.")
    ):
        abort(403)

# --------------------------------------------------
# ✅ HELPER: GET REAL LAN IP
# --------------------------------------------------
def get_local_network_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# --------------------------------------------------
# ✅ FRONTEND ROUTES
# --------------------------------------------------

# 🔹 Login page
@app.route("/")
def login_page():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "Login"),
        "index.html"
    )

# 🔹 Home page
@app.route("/home")
def home_page():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "Login"),
        "home.html"
    )

# 🔹 Admin login page
@app.route("/admin/login")
def admin_login_page():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "Final Admin"),
        "admin_login.html"
    )

# 🔹 Admin dashboard page
@app.route("/admin")
def admin_page():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "Final Admin"),
        "admin.html"
    )

# --------------------------------------------------
# ✅ STATIC FILES (CSS / JS / IMAGES)
# --------------------------------------------------

# 🔹 Serve Login folder files (style.css, script.js, images)
@app.route("/Login/<path:filename>")
def serve_login_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "Login"), filename)

# 🔹 Serve Final Admin folder files (admin.css, admin.js, images)
@app.route("/Final Admin/<path:filename>")
def serve_admin_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "Final Admin"), filename)

# 🔹 Serve admin panel page templates
@app.route("/pages/<path:filename>")
def serve_admin_pages(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "Final Admin", "pages"), filename)

# 🔹 Generic static route (backup)
@app.route("/static/<path:filename>")
def serve_static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

# --------------------------------------------------
# ✅ API STATUS CHECK
# --------------------------------------------------
@app.route("/api/status")
def api_status():
    return jsonify({
        "message": "Backend running on LAN ✅",
        "server_ip": get_local_network_ip()
    })

# --------------------------------------------------
# ✅ RUN SERVER (LAN HOSTING)
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
