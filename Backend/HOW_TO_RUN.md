# How to Run .sh Files on Linux

## Quick Answer

```bash
# 1. Make the script executable
chmod +x setup_linux_hotspot.sh

# 2. Run it with sudo (required for system changes)
sudo ./setup_linux_hotspot.sh
```

---

## Step-by-Step for Your Scripts

### Option 1: Using chmod + ./

```bash
# Navigate to Backend folder
cd ~/wifi-management/Backend

# Make scripts executable (one-time only)
chmod +x setup_linux_hotspot.sh
chmod +x start_hotspot.sh

# Run setup (need sudo for system changes)
sudo ./setup_linux_hotspot.sh

# Run start script
sudo ./start_hotspot.sh
```

### Option 2: Using bash command

```bash
# You can also run without chmod
sudo bash setup_linux_hotspot.sh
sudo bash start_hotspot.sh
```

---

## Your Two Main Scripts

### 1. `setup_linux_hotspot.sh` - Run ONCE (Initial Setup)

This installs everything and configures the system.

```bash
cd ~/wifi-management/Backend
chmod +x setup_linux_hotspot.sh
sudo ./setup_linux_hotspot.sh
```

**What it does:**
- Installs packages (hostapd, dnsmasq, etc.)
- Creates configuration files
- Sets up systemd services
- Configures networking

**When to run:** Only once, after copying files to Linux

---

### 2. `start_hotspot.sh` - Run ANYTIME (Quick Start)

This checks everything and starts the hotspot.

```bash
cd ~/wifi-management/Backend
chmod +x start_hotspot.sh
sudo ./start_hotspot.sh
```

**What it does:**
- Checks if WiFi adapter detected
- Initializes firewall rules
- Starts hotspot services
- Shows connection info

**When to run:** Every time you want to start the hotspot

---

## Complete Workflow from Windows to Linux

### On Windows (Preparing Files)

Your files are ready! Just copy them to Linux:

```powershell
# Option 1: Use WinSCP or FileZilla to copy the Backend folder

# Option 2: Use SCP from PowerShell/WSL
scp -r d:\wifi-management\Backend user@linux-vm-ip:~/wifi-management/

# Option 3: Use VMware shared folders
# VM → Settings → Options → Shared Folders
```

### On Linux VM (First Time Setup)

```bash
# 1. Navigate to folder
cd ~/wifi-management/Backend

# 2. Make scripts executable
chmod +x *.sh

# 3. Run setup script (ONCE)
sudo ./setup_linux_hotspot.sh

# Follow the on-screen instructions to:
# - Check if adapter detected
# - Edit WiFi name/password
# - Set internet interface

# 4. Start the hotspot
sudo ./start_hotspot.sh

# 5. Start Flask backend
python3 app.py
```

### On Linux VM (Every Time After Reboot)

```bash
# Option 1: Manual start
cd ~/wifi-management/Backend
sudo ./start_hotspot.sh
python3 app.py

# Option 2: Enable auto-start (recommended)
sudo hotspot enable
sudo systemctl enable wifi-backend
# Then it starts automatically on boot!
```

---

## Troubleshooting

### Error: "Permission denied"

```bash
# Make sure file is executable
chmod +x setup_linux_hotspot.sh

# Run with sudo
sudo ./setup_linux_hotspot.sh
```

### Error: "No such file or directory"

```bash
# Make sure you're in the right directory
cd ~/wifi-management/Backend
ls -la *.sh  # Should show the scripts

# Check line endings (if copied from Windows)
dos2unix setup_linux_hotspot.sh  # Fix Windows line endings
# Or: sed -i 's/\r$//' setup_linux_hotspot.sh
```

### Error: "bash: ./setup_linux_hotspot.sh: /bin/bash^M: bad interpreter"

This means Windows line endings. Fix with:

```bash
sudo apt install dos2unix
dos2unix setup_linux_hotspot.sh
dos2unix start_hotspot.sh

# Then run again
sudo ./setup_linux_hotspot.sh
```

---

## Summary - Your Action Items

1. **Copy Backend folder to Linux VM**
   ```bash
   # Use SCP, WinSCP, or shared folders
   ```

2. **Make scripts executable**
   ```bash
   cd ~/wifi-management/Backend
   chmod +x *.sh
   ```

3. **Run setup (ONCE)**
   ```bash
   sudo ./setup_linux_hotspot.sh
   ```

4. **Edit WiFi settings**
   ```bash
   sudo nano /etc/hostapd/hostapd.conf
   # Change ssid and wpa_passphrase
   ```

5. **Start hotspot**
   ```bash
   sudo ./start_hotspot.sh
   ```

6. **Start Flask**
   ```bash
   python3 app.py
   ```

7. **Connect and enjoy!** 🎉

---

## Python Scripts (Bonus)

Python scripts don't need chmod, just run with python3:

```bash
# Firewall manager
sudo python3 linux_firewall_manager.py

# Hotspot manager
sudo python3 linux_hotspot_manager.py start

# Auto monitor
sudo python3 Detection_Management/auto_monitor.py

# Flask app
python3 app.py
```

---

## Quick Reference Card

| Script | Command | When | Need sudo? |
|--------|---------|------|-----------|
| **setup_linux_hotspot.sh** | `sudo ./setup_linux_hotspot.sh` | Once (initial setup) | ✅ Yes |
| **start_hotspot.sh** | `sudo ./start_hotspot.sh` | Every time | ✅ Yes |
| **linux_firewall_manager.py** | `sudo python3 linux_firewall_manager.py` | Test/manual | ✅ Yes |
| **linux_hotspot_manager.py** | `sudo python3 linux_hotspot_manager.py start` | Alternative to script | ✅ Yes |
| **app.py** | `python3 app.py` | Every time | ❌ No |
| **auto_monitor.py** | `sudo python3 Detection_Management/auto_monitor.py` | When monitoring | ✅ Yes |

---

**Ready to start!** Just run `chmod +x *.sh` then `sudo ./setup_linux_hotspot.sh` 🚀
