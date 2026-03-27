# WiFi Management System

## Overview

A full-stack web application for managing a campus Wi-Fi network. It provides:

- Student authentication and captive-portal access control.
- Admin dashboard with client management, bandwidth control, web-filtering, logs, and reporting.
- RESTful API built with **Flask** and **MongoDB**.
- Modern, responsive frontend built with vanilla HTML/CSS/JS.
- Real-time packet monitoring via **tshark** using a **TP-Link USB Wi-Fi adapter**.

## Features

- **Student portal** – login, view usage, request bandwidth.
- **Admin portal** – manage clients, block/unblock sites, toggle category filters, view logs, generate reports, bulk CSV upload.
- **Network security** – Captive portal, LAN-only access, IP-based session tracking, iptables firewall.
- **Traffic monitoring** – Live packet capture on the hotspot interface with tshark.
- **Dynamic UI** – smooth animations, dark mode, glass-morphism styling.

---

## Hardware Requirements

| Role            | Device                                                           |
| --------------- | ---------------------------------------------------------------- |
| Hotspot (AP)    | **TP-Link USB Wi-Fi Adapter** (e.g. TL-WN823N, Archer T2U, etc.) |
| Internet uplink | Built-in Wi-Fi / Ethernet connected to the internet              |
| Server          | Linux machine (Ubuntu 22.04+ recommended)                        |

> **TP-Link adapter interface name**: `wlx782051ac644f`  
> **Internet interface name**: `wlp0s20f3`  
> Verify your own interfaces with: `ip link show` or `iwconfig`

---

## Project Structure

```
wifi-management/
├─ Backend/
│  ├─ app.py                        # Flask entry point
│  ├─ admin_routes.py               # Admin API routes
│  ├─ auth_routes.py                # Auth API routes
│  ├─ filtering_routes.py           # Web-filter routes
│  ├─ db.py                         # MongoDB connection
│  ├─ linux_hotspot_manager.py      # Hotspot start/stop control
│  ├─ linux_firewall_manager.py     # iptables / captive portal
│  ├─ bandwidth_manager.py          # Per-client bandwidth (tc/HTB)
│  ├─ dns_filtering_manager.py      # dnsmasq-based DNS blocking
│  ├─ domain_resolver_service.py    # Domain → IP resolution
│  ├─ setup_complete_system.sh      # ⚙️  First-time full setup
│  ├─ start_system.sh               # 🚀 Daily startup script
│  ├─ setup_tshark.sh               # 📡 tshark monitoring setup
│  └─ Frontend/
│     ├─ Login/                     # Student login/home pages
│     └─ Final Admin/               # Admin dashboard
└─ README.md
```

---

## First-Time Setup (Run Once)

### 1. Clone the repository

```bash
git clone https://github.com/Hitesh1477/wifi-management.git
cd wifi-management
```

### 2. Plug in TP-Link USB Wi-Fi Adapter

Connect the TP-Link adapter before proceeding. Verify it is detected:

```bash
ip link show
# Look for an interface starting with wlx... (e.g. wlx782051ac644f)

iwconfig
# Should show the wireless interface
```

If your adapter interface name differs from `wlx782051ac644f`, update it in:

- `Backend/setup_complete_system.sh` → `HOTSPOT_INTERFACE=`
- `Backend/start_system.sh` → `HOTSPOT_INTERFACE=`

### 3. Run the master setup script

```bash
cd Backend
sudo bash setup_complete_system.sh
```

This script automatically:

- Installs `hostapd`, `dnsmasq`, `iptables`, `tshark`, `wireshark`
- Configures `hostapd` (Wi-Fi Access Point on the TP-Link adapter)
- Configures `dnsmasq` (DHCP & DNS server)
- Prevents NetworkManager from hijacking the hotspot interface
- Enables IP forwarding
- Sets up tshark permissions for non-root packet capture

> **After this script**, log out and log back in so the `wireshark` group takes effect.

### 4. Set up the database (MongoDB)

**Install MongoDB Community Server** and ensure it is running:

```bash
sudo systemctl start mongod
sudo systemctl enable mongod
```

Then run the database initialisation script:

```bash
cd Backend
python3 setup_database.py
```

Or manually in **MongoDB Compass**:

- Create database: `studentapp`
- Create collections: `users`, `admins`, `active_sessions`, `blocked_users`, `web_filter`, `logs`

Create an admin account (insert into `admins` collection):

```python
from werkzeug.security import generate_password_hash
print(generate_password_hash('Admin@123'))
```

Insert document: `{ "username": "admin", "password": "<hash from above>" }`

### 5. Install Python dependencies

```bash
cd Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt      # or: pip install flask flask-cors pymongo werkzeug PyJWT
```

### 6. Set up tshark monitoring (if not done by setup_complete_system.sh)

```bash
sudo bash Backend/setup_tshark.sh
# Then log out and log back in
```

---

## Daily Startup (Every Boot)

### Step 1 – Start the Hotspot (requires root)

```bash
sudo bash /home/nikhil/wifi-management/Backend/start_system.sh
```

This will:

1. Configure the TP-Link adapter (`wlx782051ac644f`) with IP `192.168.50.1`
2. Start `dnsmasq` (DHCP + DNS)
3. Start `hostapd` (Wi-Fi Access Point)
4. Apply iptables firewall + captive portal rules

**Expected output:**

```
✅ Interface configured with IP 192.168.50.1
✅ dnsmasq is running
✅ hostapd is running
✅ WiFi Hotspot Started!
  📶 SSID: CampusWiFi
  🔐 Password: campus123
  🌐 Gateway IP: 192.168.50.1
```

### Step 2 – Start the Flask Backend

```bash
cd /home/nikhil/wifi-management/Backend
source venv/bin/activate
sudo python3 app.py
```

The backend will be available at: `http://192.168.50.1:5000`

### Step 3 – Access the Portals

| Portal          | URL                                    |
| --------------- | -------------------------------------- |
| Student Login   | `http://192.168.50.1:5000/`            |
| Admin Login     | `http://192.168.50.1:5000/admin/login` |
| Admin Dashboard | `http://192.168.50.1:5000/admin`       |

Connect any device to the **CampusWiFi** network and open any URL — it will redirect to the login page.

---

## Monitoring with TP-Link Adapter (tshark)

The TP-Link adapter (`wlx782051ac644f`) is used both as the **hotspot AP** and as the **monitoring interface**. Use `tshark` to capture live traffic on it.

### Live packet capture

```bash
sudo tshark -i wlx782051ac644f
```

### Capture with DNS queries (useful for web-filter debugging)

```bash
sudo tshark -i wlx782051ac644f -f "udp port 53" -Y "dns"
```

### Capture HTTP/HTTPS traffic

```bash
sudo tshark -i wlx782051ac644f -f "tcp port 80 or tcp port 443"
```

### Monitor a specific client IP (e.g. 192.168.50.105)

```bash
sudo tshark -i wlx782051ac644f -f "host 192.168.50.105"
```

### Save capture to a file for analysis

```bash
sudo tshark -i wlx782051ac644f -w /tmp/capture.pcap
# Open capture.pcap in Wireshark for full analysis
wireshark /tmp/capture.pcap
```

### Show real-time bandwidth per client

```bash
sudo tshark -i wlx782051ac644f -q -z conv,ip
```

> **Note**: If you get a permission error, ensure you have logged out and back in after running `setup_tshark.sh`, and that your user is in the `wireshark` group:
>
> ```bash
> groups | grep wireshark
> ```

---

## Hotspot Management Commands

```bash
# Check hotspot status
sudo systemctl status hostapd
sudo systemctl status dnsmasq

# List connected clients
iw dev wlx782051ac644f station dump

# Restart hotspot (if something goes wrong)
sudo bash /home/nikhil/wifi-management/Backend/start_system.sh

# Stop hotspot manually
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq

# Check firewall rules
sudo iptables -L -n -v
sudo iptables -t nat -L -n -v

# Reset firewall (clean slate)
cd /home/nikhil/wifi-management/Backend
sudo python3 reset_firewall.py
```

---

## API Endpoints

### Auth routes (`/api/auth`)

| Method | Endpoint       | Description                    |
| ------ | -------------- | ------------------------------ |
| POST   | `/signup`      | Register a student             |
| POST   | `/login`       | Student login, returns JWT     |
| POST   | `/logout`      | End session                    |
| POST   | `/admin/login` | Admin login, returns admin JWT |

### Admin routes (`/api/admin`)

| Method | Endpoint                | Description                                           |
| ------ | ----------------------- | ----------------------------------------------------- |
| GET    | `/clients`              | List all student clients                              |
| POST   | `/clients`              | Add a new client                                      |
| PATCH  | `/clients/<id>`         | Update client (bandwidth limit, block status)         |
| GET    | `/filtering`            | Retrieve manual block list and category states        |
| POST   | `/filtering/sites`      | Add a manual block URL                                |
| DELETE | `/filtering/sites`      | Remove a manual block URL                             |
| POST   | `/filtering/categories` | Toggle a category's active flag                       |
| GET    | `/logs`                 | Fetch recent log entries                              |
| GET    | `/stats`                | Dashboard summary (client count, total data, threats) |
| POST   | `/reports`              | Generate a report (`type` and `range` in body)        |
| POST   | `/bulk-upload`          | Upload CSV to add multiple clients                    |

All admin endpoints require: `Authorization: Bearer <token>` with `role: "admin"`.

---

## Troubleshooting

| Problem                        | Fix                                                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| TP-Link adapter not detected   | Run `lsusb` to check if adapter is recognized. May need driver: `sudo apt install linux-generic-hwe-22.04` |
| `hostapd` fails to start       | Check logs: `journalctl -u hostapd -n 30 --no-pager`. Ensure no other process uses the interface.          |
| `dnsmasq` fails to start       | Port 53 conflict: `sudo systemctl stop systemd-resolved` then retry                                        |
| tshark permission denied       | Log out and back in after `setup_tshark.sh`. Verify: `groups \| grep wireshark`                            |
| Clients can't get IP           | Restart dnsmasq: `sudo systemctl restart dnsmasq`                                                          |
| Captive portal not redirecting | Re-run firewall: `sudo bash start_system.sh`                                                               |
| MongoDB connection error       | Ensure MongoDB is running: `sudo systemctl status mongod`                                                  |

---

## Auto-start on Boot (Optional)

```bash
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo systemctl enable mongod
```

---

## 🚀 How to Run the Project Daily (Line by Line)

Copy-paste these commands **every time you start the system**. Run them in order.

### Terminal 1 — Start Hotspot + Firewall (as root)

```basha
# 1. Go to the project backend folder
cd /home/nikhil/wifi-management/Backend

# 2. Start the hotspot (TP-Link adapter), DHCP, DNS, and captive portal firewall
sudo bash start_system.sh
```

---

### Terminal 2 — Start Flask Backend

```bash
# 3. Go to the backend folder
cd /home/nikhil/wifi-management/Backend

# 4. Activate the Python virtual environment
source venv/bin/activate

# 5. Start the Flask server (needs sudo for firewall + bandwidth control)
python3 app.py
```

The backend is now live at: **`http://192.168.50.1:5000`**

---

### Terminal 3 — Start TP-Link Monitoring (tshark)

cd /home/nikhil/wifi-management/Backend/Detection_Management
python3 auto_monitor.py wlx782051ac644f
python3 auto_monitor.py list 

Open a third terminal and run any of these depending on what you want to monitor:

```bash
# 6a. Monitor ALL traffic on the TP-Link hotspot interface
sudo tshark -i wlx782051ac644f

# 6b. Monitor only DNS queries (what sites clients are trying to visit)
sudo tshark -i wlx782051ac644f -f "udp port 53" -Y "dns"

# 6c. Monitor a specific client IP (replace with actual client3 IP)
sudo tshark -i wlx782051ac644f -f "host 192.168.50.105"

# 6d. See real-time data usage per IP address
sudo tshark -i wlx782051ac644f -q -z conv,ip
```

---

### Access the Portals (from any device on CampusWiFi)

```
Student Login   →  http://192.168.50.1:5000/
Admin Login     →  http://192.168.50.1:5000/admin/login
Admin Dashboard →  http://192.168.50.1:5000/admin
```

---

### Quick Status Checks

```bash
# Check if hotspot is running
sudo systemctl status hostapd
sudo systemctl status dnsmasq

# List currently connected Wi-Fi clients
iw dev wlx782051ac644f station dump

# Check MongoDB is running
sudo systemctl status mongod

# Check firewall rules
sudo iptables -L -n -v
```

---
For auto updating dnsmasq blocklist, run:
sudo ./setup_dnsmasq_autoupdate.sh nikhil

## License

This project is licensed under the MIT License.
