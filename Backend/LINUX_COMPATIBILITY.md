# Linux Compatibility Guide for Your WiFi Management Project

## Summary: What Works and What Needs Editing

### ✅ Will Work As-Is (No Changes Needed)

1. **Flask Backend Core**
   - `app.py` - Cross-platform ✓
   - `auth_routes.py` - Cross-platform ✓
   - `admin_routes.py` - Cross-platform ✓
   - `db.py` - MongoDB works on Linux ✓
   - `models/` - Cross-platform ✓

2. **Frontend**
   - All HTML/CSS/JS files work identically ✓
   - `Frontend/Login/` - No changes needed ✓
   - `Frontend/Final Admin/` - No changes needed ✓

3. **Database & ML**
   - MongoDB works on Linux (install with `sudo apt install mongodb`)
   - All ML model files (.py) are cross-platform
   - `Detection_Management/ml_random_forest.py` ✓
   - `Detection_Management/bandwidth_ml_model.py` ✓

---

### ⚠️ Needs Minor Edits

1. **filtering_routes.py**
   - **Issue**: Currently tries to import `firewall_manager` (Windows-specific)
   - **Solution**: Update import to use `linux_firewall_manager`

2. **Detection_Management/capture.py**
   - **Issue**: Default interface is `"Wi-Fi"` (Windows naming)
   - **Solution**: Change default to `"wlan0"` for Linux

3. **Detection_Management/auto_monitor.py**
   - **Issue**: Default interface is `"Wi-Fi"`, has Windows hotspot logic
   - **Solution**: Update to use Linux interface naming

---

### ❌ Won't Work on Linux (Need Replacement)

1. **firewall_manager.py** (if it exists)
   - Windows Firewall is not available on Linux
   - **Solution**: Already created `linux_firewall_manager.py` ✓

2. **Windows-specific network interface names**
   - Windows uses: `"Wi-Fi"`, `"Local Area Connection* 2"`
   - Linux uses: `wlan0`, `eth0`, `enp0s3`, etc.

---

## Required Edits for Linux Compatibility

### 1. Update `filtering_routes.py`

**Current (lines 3-7):**
```python
try:
    from firewall_manager import update_firewall_rules
except ImportError:
    # Graceful fallback if running in non-admin/limited env
    def update_firewall_rules(): pass
```

**Change to:**
```python
try:
    from linux_firewall_manager import update_firewall_rules
except ImportError:
    # Graceful fallback if running in non-admin/limited env
    def update_firewall_rules(): pass
```

---

### 2. Update `Detection_Management/capture.py`

**Current (line 8):**
```python
def start_capture_stream(interface="Wi-Fi"):
```

**Change to:**
```python
def start_capture_stream(interface="wlan0"):
```

**Also update error messages:**
```python
# Line 45-46: Keep tshark messages  (tshark works on Linux too!)
# Line 49: Update to:
print("❌ Permission denied. Run with sudo to capture packets")
```

---

### 3. Update `Detection_Management/auto_monitor.py`

**Current (line 15):**
```python
def auto_monitor(interface="Wi-Fi", interval_minutes=1, ml_interval_minutes=5):
```

**Change to:**
```python
def auto_monitor(interface="wlan0", interval_minutes=1, ml_interval_minutes=5):
```

**Current (lines 69-103): Windows-specific logic**

**Change to:**
```python
if __name__ == "__main__":
    import argparse
    import subprocess
    
    parser = argparse.ArgumentParser(description="Monitor network traffic")
    parser.add_argument("interface", nargs="?", default="wlan0", 
                        help="Network interface (default: wlan0, use 'list' to show all)")
    args = parser.parse_args()
    
    interface = args.interface
    
    # List interfaces if requested
    if interface.lower() == "list":
        print("📋 Available network interfaces:")
        result = subprocess.run(["tshark", "-D"], capture_output=True, text=True)
        print(result.stdout)
        sys.exit(0)
    
    print(f"📡 Using interface: {interface}")
    auto_monitor(interface)
```

---

### 4. Install tshark on Linux

Your capture scripts use `tshark`, which works on Linux too!

```bash
sudo apt install tshark

# Allow non-root packet capture
sudo dpkg-reconfigure wireshark-common
# Select "Yes" when asked

# Add user to wireshark group
sudo usermod -a -G wireshark $USER
# Log out and back in for this to take effect
```

---

## Step-by-Step Migration Plan

### Option 1: Quick Edits (Recommended)

Just make the 3 small edits above, and your entire project will work on Linux!

```bash
# 1. Edit filtering_routes.py
nano Backend/filtering_routes.py
# Change line 4: from firewall_manager to linux_firewall_manager

# 2. Edit capture.py
nano Backend/Detection_Management/capture.py
# Change line 8: interface="Wi-Fi" to interface="wlan0"
# Change line 49: "Run as Administrator" to "Run with sudo"

# 3. Edit auto_monitor.py
nano Backend/Detection_Management/auto_monitor.py
# Change line 15: interface="Wi-Fi" to interface="wlan0"
# Change line 81: default="Wi-Fi" to default="wlan0"
# Remove lines 94-101 (Windows hotspot logic)
```

### Option 2: Platform Detection (Advanced)

Create a compatibility layer that works on both Windows AND Linux.

**Create `Backend/platform_adapter.py`:**
```python
import platform
import sys

# Detect platform
IS_LINUX = platform.system() == 'Linux'
IS_WINDOWS = platform.system() == 'Windows'

# Firewall manager
if IS_LINUX:
    try:
        from linux_firewall_manager import update_firewall_rules
    except ImportError:
        def update_firewall_rules(): pass
elif IS_WINDOWS:
    try:
        from firewall_manager import update_firewall_rules
    except ImportError:
        def update_firewall_rules(): pass
else:
    def update_firewall_rules(): pass

# Default network interface
if IS_LINUX:
    DEFAULT_INTERFACE = "wlan0"
elif IS_WINDOWS:
    DEFAULT_INTERFACE = "Wi-Fi"
else:
    DEFAULT_INTERFACE = None
```

**Then update filtering_routes.py:**
```python
from platform_adapter import update_firewall_rules
```

**And update capture.py and auto_monitor.py:**
```python
from platform_adapter import DEFAULT_INTERFACE

def start_capture_stream(interface=DEFAULT_INTERFACE):
    ...
```

---

## What About MongoDB?

MongoDB works great on Linux! Install it:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y mongodb

# Start MongoDB
sudo systemctl start mongodb
sudo systemctl enable mongodb  # Auto-start on boot

# Verify it's running
sudo systemctl status mongodb

# Test connection
mongosh  # or 'mongo' on older versions
```

Your existing `db.py` will work without any changes! The connection string is the same:
```python
mongodb://localhost:27017/
```

---

## Testing Checklist

After making the edits, test each component:

### 1. Flask Backend
```bash
cd Backend
python3 app.py
# Should start on http://0.0.0.0:5000
```

### 2. Database Connection
```bash
python3 -c "from db import users_collection; print(users_collection.count_documents({}))"
# Should print number of users (or 0 if empty)
```

### 3. Firewall Integration
```bash
sudo python3 -c "from linux_firewall_manager import update_firewall_rules; update_firewall_rules()"
# Should update iptables rules
```

### 4. Packet Capture
```bash
# List interfaces
python3 Detection_Management/capture.py list

# Test capture (Ctrl+C to stop)
sudo python3 Detection_Management/auto_monitor.py wlan0
```

### 5. Web Filtering
```bash
# Start hotspot
cd Backend
sudo ./start_hotspot.sh

# Start Flask
python3 app.py

# Test blocking via API
curl -X POST http://localhost:5000/api/admin/filtering/sites \
  -H "Content-Type: application/json" \
  -d '{"url": "example.com"}'
```

---

## Full File Comparison

| Component | Windows | Linux | Status |
|-----------|---------|-------|--------|
| **Flask App** | app.py | app.py | ✅ Same |
| **Routes** | *_routes.py | *_routes.py | ✅ Same |
| **Frontend** | HTML/CSS/JS | HTML/CSS/JS | ✅ Same |
| **Database** | MongoDB | MongoDB | ✅ Same |
| **Firewall** | firewall_manager.py | **linux_firewall_manager.py** | ⚠️ Different |
| **Hotspot** | Windows Hotspot | **linux_hotspot_manager.py** | ⚠️ Different |
| **Packet Capture** | tshark + "Wi-Fi" | tshark + "wlan0" | ⚠️ Minor edit |
| **ML Models** | *.py | *.py | ✅ Same |

---

## Quick Answer

**95% of your project will work as-is on Linux!**

You only need to make **3 small edits**:

1. Change firewall import in `filtering_routes.py`
2. Change default interface in `capture.py` 
3. Change default interface in `auto_monitor.py`

Everything else (Flask, MongoDB, ML, Frontend) is cross-platform and works identically! 🎉

---

## Recommended Approach

**Do this on your Linux VM:**

```bash
# 1. Copy project to Linux
# (already assumed done)

# 2. Make the 3 edits above
# (5 minutes)

# 3. Install dependencies
sudo apt install mongodb tshark
pip3 install flask flask-cors pymongo

# 4. Run setup
cd Backend
chmod +x setup_linux_hotspot.sh
sudo ./setup_linux_hotspot.sh

# 5. Start everything
sudo ./start_hotspot.sh
python3 app.py

# Done! 🚀
```

Your admin panel, user authentication, ML detection, bandwidth management - **all of it will work!** You just need to use the Linux-specific firewall and hotspot managers instead of the Windows ones.
