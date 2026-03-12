from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS
import os
import socket
import ipaddress

# ✅ Import DB collections (ONLY from db.py)
from db import users_collection, admins_collection, sessions_collection

# ✅ Import Blueprints
from admin_routes import admin_routes
from auth_routes import auth_routes
from filtering_routes import filtering_blueprint

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
app.register_blueprint(filtering_blueprint, url_prefix="/api/admin")

# --------------------------------------------------
# ✅ ALLOW ONLY LOCAL NETWORK (Wi-Fi)
# --------------------------------------------------
@app.before_request
def allow_lan_only():
    raw_ip = request.remote_addr or ""
    if not raw_ip:
        abort(403)

    try:
        client_ip = ipaddress.ip_address(raw_ip)
    except ValueError:
        abort(403)

    if client_ip.is_loopback:
        return

    if not client_ip.is_private:
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
# --------------------------------------------------
# ✅ RUN SERVER (LAN HOSTING)
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False) # Disable debug to prevent double-execution on reload
