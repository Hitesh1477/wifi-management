# Linux WiFi Hotspot with Web Filtering

Complete solution for running a WiFi hotspot on Linux with integrated web filtering using TP-Link WN823n USB adapter.

## 🎯 Features

- **WiFi Hotspot**: Create a WiFi access point using TP-Link WN823n adapter
- **Web Filtering**: Block websites by domain or category using iptables
- **User Authentication**: Integration with Flask backend for user login
- **Dynamic Configuration**: Update filtering rules via admin panel
- **Bandwidth Management**: Control bandwidth per client (requires tc configuration)
- **Auto-Start**: Systemd services for automatic startup on boot

## 📋 Requirements

### Hardware
- TP-Link TL-WN823n USB WiFi Adapter (RTL8192EU chipset)
- Linux machine (VM or physical) with internet connection
- At least 1 network interface for internet (eth0, enp0s3, etc.)

### Software
- Ubuntu 20.04+ or Debian-based Linux
- Python 3.8+
- MongoDB (for backend database)
- VMware (if using VM) with USB passthrough enabled

## 🚀 Quick Start

### 1. Transfer Files to Linux VM

Copy the entire `Backend` folder to your Linux VM:

```bash
# On Windows (from WSL or Git Bash)
scp -r Backend your-username@linux-vm-ip:~/wifi-management/

# OR use VMware shared folders
# OR use a USB drive
```

### 2. Run Setup Script

On your Linux VM:

```bash
cd ~/wifi-management/Backend
chmod +x setup_linux_hotspot.sh
sudo ./setup_linux_hotspot.sh
```

This will:
- Install all required packages (hostapd, dnsmasq, iptables, etc.)
- Configure WiFi adapter and network interfaces
- Create systemd services
- Set up firewall rules

### 3. Install WiFi Driver (if needed)

If your TP-Link adapter is not detected:

```bash
# Check if detected
lsusb | grep -i realtek
iwconfig

# If not detected, install driver
git clone https://github.com/Mange/rtl8192eu-linux-driver
cd rtl8192eu-linux-driver
sudo dkms add .
sudo dkms install rtl8192eu/1.0
sudo reboot
```

### 4. Configure Hotspot Settings

Edit the hotspot configuration:

```bash
sudo nano /etc/hostapd/hostapd.conf
```

Change these values:
- `ssid`: Your WiFi network name
- `wpa_passphrase`: Your WiFi password (min 8 characters)
- `channel`: WiFi channel (1-11 for 2.4GHz)

### 5. Update Internet Interface

Find your internet interface:

```bash
ip route | grep default
# Look for the interface name after "dev" (e.g., eth0, enp0s3)
```

Update the interface in `linux_firewall_manager.py`:

```bash
nano linux_firewall_manager.py
# Change line: self.internet_interface = "eth0"  # to your interface
```

### 6. Start Everything

```bash
# Make script executable
chmod +x start_hotspot.sh

# Run quick start
sudo ./start_hotspot.sh
```

This will:
- Check adapter detection
- Setup firewall and NAT
- Start hotspot services
- Display connection information

### 7. Connect and Test

1. **Connect to WiFi**: Use your phone/laptop to connect to the hotspot
2. **Access Admin Panel**: Open browser to `http://192.168.50.1:5000/admin/login`
3. **Test Filtering**: Block a website from admin panel and verify it's blocked on client

## 📁 File Structure

```
Backend/
├── linux_firewall_manager.py    # iptables firewall management
├── linux_hotspot_manager.py     # Hotspot control (start/stop/status)
├── domain_resolver_service.py   # Background IP refresh service
├── setup_linux_hotspot.sh       # Initial setup script
├── start_hotspot.sh             # Quick start script
├── LINUX_CONFIG_GUIDE.md        # Configuration reference
├── app.py                       # Flask backend (existing)
├── filtering_routes.py          # Filtering API endpoints (existing)
└── ... (other existing files)
```

## 🔧 Usage

### Control Hotspot

```bash
# Start hotspot
sudo hotspot start

# Stop hotspot
sudo hotspot stop

# Restart hotspot
sudo hotspot restart

# Check status
sudo hotspot status

# Enable auto-start on boot
sudo hotspot enable

# Disable auto-start
sudo hotspot disable
```

### Control Flask Backend

```bash
# Start backend
sudo systemctl start wifi-backend

# Stop backend
sudo systemctl stop wifi-backend

# Check status
sudo systemctl status wifi-backend

# View logs
sudo journalctl -u wifi-backend -f

# Enable on boot
sudo systemctl enable wifi-backend
```

### Control Domain Resolver

```bash
# Start domain resolver
sudo systemctl start domain-resolver

# Stop domain resolver
sudo systemctl stop domain-resolver

# Check status
sudo systemctl status domain-resolver

# View logs
sudo journalctl -u domain-resolver -f
```

### Manual Firewall Management

```bash
# Update firewall from database
cd Backend
sudo python3 linux_firewall_manager.py

# Check rules
sudo iptables -L -n -v

# Check NAT rules
sudo iptables -t nat -L -n -v
```

## 🌐 Network Architecture

```
[Internet] 
    ↓
[eth0: Internet Interface]
    ↓
[Linux VM with iptables NAT]
    ↓
[wlan0: 192.168.50.1 - Hotspot Interface]
    ↓
[WiFi Clients: 192.168.50.10-100]
```

- **Hotspot Network**: 192.168.50.0/24
- **Gateway**: 192.168.50.1
- **DHCP Range**: 192.168.50.10 - 192.168.50.100
- **DNS**: 8.8.8.8, 8.8.4.4 (filtered through local DNS)

## 🛡️ Web Filtering

### How It Works

1. **DNS Filtering**: Dnsmasq resolves blocked domains to 127.0.0.1
2. **iptables Blocking**: Firewall blocks traffic to resolved IPs
3. **Dynamic Updates**: Domain IPs refreshed every hour
4. **Category Filtering**: Block entire categories (Gaming, Social Media, etc.)

### Block a Website

Via API:
```bash
curl -X POST http://192.168.50.1:5000/api/admin/filtering/sites \
  -H "Content-Type: application/json" \
  -d '{"url": "example.com"}'
```

Via Admin Panel:
1. Login to admin panel
2. Go to "Web Filtering" tab
3. Add domain and click "Block"

### Unblock a Website

```bash
curl -X DELETE http://192.168.50.1:5000/api/admin/filtering/sites \
  -H "Content-Type: application/json" \
  -d '{"url": "example.com"}'
```

## 🐛 Troubleshooting

### WiFi Adapter Not Detected

```bash
# Check USB devices
lsusb | grep -i realtek

# Check VMware USB passthrough
# In VMware: VM → Removable Devices → Realtek... → Connect

# Check kernel messages
dmesg | tail -20

# Install driver manually
git clone https://github.com/Mange/rtl8192eu-linux-driver
cd rtl8192eu-linux-driver
sudo dkms add .
sudo dkms install rtl8192eu/1.0
sudo modprobe 8192eu
```

### hostapd Won't Start

```bash
# Check detailed errors
sudo hostapd -dd /etc/hostapd/hostapd.conf

# Common fixes:

# 1. NetworkManager conflict
sudo nmcli device set wlan0 managed no

# OR edit /etc/NetworkManager/NetworkManager.conf:
[keyfile]
unmanaged-devices=interface-name:wlan0

# 2. Interface in use
sudo systemctl stop wpa_supplicant
sudo pkill wpa_supplicant

# 3. Wrong channel
# Edit /etc/hostapd/hostapd.conf and change channel
```

### No Internet on Clients

```bash
# Check IP forwarding
cat /proc/sys/net/ipv4/ip_forward  # Should be 1
sudo sysctl -w net.ipv4.ip_forward=1

# Check NAT rules
sudo iptables -t nat -L -n -v | grep MASQUERADE

# Re-setup NAT
sudo python3 linux_firewall_manager.py

# Check routing
ip route
```

### Web Filtering Not Working

```bash
# Check filter rules
sudo iptables -L FORWARD -n -v | grep DROP

# Update from database
cd Backend
sudo python3 -c "from linux_firewall_manager import update_firewall_rules; update_firewall_rules()"

# Check DNS
nslookup facebook.com 192.168.50.1

# Check dnsmasq logs
sudo tail -f /var/log/dnsmasq.log
```

### MongoDB Connection Error

```bash
# Install MongoDB if not installed
sudo apt install mongodb

# Start MongoDB
sudo systemctl start mongodb
sudo systemctl enable mongodb

# Check if running
sudo systemctl status mongodb

# Test connection
mongosh  # OR mongo (older versions)
```

## 📊 Monitoring

### View Connected Clients

```bash
# List connected devices
sudo iw dev wlan0 station dump

# Count clients
sudo iw dev wlan0 station dump | grep Station | wc -l

# View DHCP leases
cat /var/lib/misc/dnsmasq.leases
```

### View Network Traffic

```bash
# Install iftop
sudo apt install iftop

# Monitor wlan0 traffic
sudo iftop -i wlan0

# Monitor with vnstat
sudo apt install vnstat
vnstat -i wlan0
```

### View Logs

```bash
# Hotspot logs
sudo journalctl -u hostapd -f
sudo journalctl -u dnsmasq -f

# Flask backend logs
sudo journalctl -u wifi-backend -f

# Domain resolver logs
sudo journalctl -u domain-resolver -f

# Firewall logs (if enabled)
sudo dmesg | grep iptables
```

## 🔐 Security Notes

- Default hotspot password is `Password@123` - **CHANGE THIS!**
- Admin panel is accessible to all hotspot clients
- Consider adding HTTPS with Let's Encrypt
- Firewall only filters domains, not IPs directly
- Use strong passwords for MongoDB and admin accounts

## 🚀 Advanced Features

### Enable Logging for Blocked Traffic

```bash
# Add logging rule before DROP rules
sudo iptables -I FORWARD -s 192.168.50.0/24 -j LOG --log-prefix "BLOCKED: " --log-level 4

# View logs
sudo dmesg | grep BLOCKED
```

### Bandwidth Limiting (tc)

```bash
# Install tc
sudo apt install iproute2

# Limit to 1Mbps per client
sudo tc qdisc add dev wlan0 root handle 1: htb default 10
sudo tc class add dev wlan0 parent 1: classid 1:10 htb rate 1mbit
```

### Port Forwarding

```bash
# Forward port 80 to specific client
sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j DNAT --to 192.168.50.50:80
```

## 📝 License

This project integrates with your existing WiFi management system.

## 🆘 Support

If issues persist:
1. Check all logs: `sudo journalctl -xe`
2. Verify adapter with `lsusb` and `iwconfig`
3. Review `/var/log/syslog` for errors
4. Test manually: `sudo hostapd -dd /etc/hostapd/hostapd.conf`

---

**Ready to go!** Connect your TP-Link adapter, run the setup, and enjoy your Linux-powered hotspot with web filtering! 🎉
