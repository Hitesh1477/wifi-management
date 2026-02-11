# WiFi Hotspot Configuration Guide

This file contains example configurations for your Linux WiFi hotspot.
Copy these files to your Linux VM and modify as needed.

## hostapd.conf
Location: `/etc/hostapd/hostapd.conf`

```conf
# WiFi Interface (change if your adapter shows as wlan1, etc.)
interface=wlan0
driver=nl80211

# Network Settings
ssid=MyWiFiHotspot          # Change this to your desired WiFi name
hw_mode=g                   # 2.4GHz (use 'a' for 5GHz if supported)
channel=6                   # WiFi channel (1-11 for 2.4GHz)
ieee80211n=1                # Enable 802.11n
wmm_enabled=1               # Enable WMM (required for 802.11n)

# Security Settings
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0     # Set to 1 to hide SSID
wpa=2                       # WPA2
wpa_passphrase=Password@123 # Change this to your password (min 8 chars)
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

## dnsmasq.conf
Location: `/etc/dnsmasq.conf`

```conf
# Interface to listen on
interface=wlan0

# Never forward plain names
domain-needed
bogus-priv

# DHCP range (adjust subnet if needed)
dhcp-range=192.168.50.10,192.168.50.100,255.255.255.0,24h

# Gateway (this machine)
dhcp-option=3,192.168.50.1

# DNS server (this machine)
dhcp-option=6,192.168.50.1

# Upstream DNS servers
no-resolv
server=8.8.8.8
server=8.8.4.4
server=1.1.1.1

# Logging
log-queries
log-dhcp
log-facility=/var/log/dnsmasq.log

# Cache
cache-size=500

# Domain blocking examples (add blocked domains here)
# Domains will resolve to localhost, effectively blocking them
address=/steampowered.com/127.0.0.1
address=/twitch.tv/127.0.0.1
address=/facebook.com/127.0.0.1
# Add more as needed...
```

## Network Interface Configuration
Location: `/etc/network/interfaces.d/wlan0`

```
auto wlan0
iface wlan0 inet static
    address 192.168.50.1
    netmask 255.255.255.0
```

## Alternative: Using NetworkManager

If your system uses NetworkManager, you can configure the interface with:

```bash
sudo nmcli connection add type wifi ifname wlan0 con-name hotspot autoconnect yes \
  ssid MyWiFiHotspot \
  mode ap \
  ipv4.method shared \
  ipv4.addresses 192.168.50.1/24

sudo nmcli connection modify hotspot wifi-sec.key-mgmt wpa-psk
sudo nmcli connection modify hotspot wifi-sec.psk "Password@123"
```

## Firewall Configuration

The firewall is managed by the Python scripts, but here's the manual iptables setup for reference:

```bash
# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf

# Set up NAT (replace eth0 with your internet interface)
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# Allow forwarding from hotspot to internet
sudo iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
sudo iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# Save rules
sudo netfilter-persistent save
# OR
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

## Finding Your Internet Interface

Run this command to find your internet interface:

```bash
ip route | grep default
```

Look for the interface name after "dev" (usually eth0, enp0s3, ens33, etc.)

## Troubleshooting

### WiFi adapter not detected
```bash
# Check USB devices
lsusb | grep -i realtek

# Check wireless interfaces
iwconfig

# Check kernel messages
dmesg | grep -i 8192eu
```

### hostapd fails to start
```bash
# Check detailed error
sudo hostapd -dd /etc/hostapd/hostapd.conf

# Common issues:
# - Interface already in use by NetworkManager
# - Wrong driver specified
# - Channel not supported
```

### NetworkManager conflicts
```bash
# Stop NetworkManager from managing wlan0
sudo nano /etc/NetworkManager/NetworkManager.conf

# Add under [keyfile]:
[keyfile]
unmanaged-devices=interface-name:wlan0

# Restart NetworkManager
sudo systemctl restart NetworkManager
```

### No internet on clients
```bash
# Check IP forwarding
cat /proc/sys/net/ipv4/ip_forward  # Should be 1

# Check NAT rules
sudo iptables -t nat -L -n -v

# Check routing
ip route
```

### Web filtering not working
```bash
# Check iptables FORWARD rules
sudo iptables -L FORWARD -n -v

# Test domain resolution
nslookup steampowered.com 192.168.50.1

# Check dnsmasq logs
sudo tail -f /var/log/dnsmasq.log
```
