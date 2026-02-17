#!/bin/bash
# Cleanup script - removes all filtering rules and restarts the system

echo "🧹 Cleaning up filtering test..."
echo ""

# Remove all blocked IPs
echo "Removing blocked IPs..."
python3 <<'PYEOF'
import sys
sys.path.insert(0, '/home/nikhil/wifi-management/Backend')

from linux_firewall_manager import get_firewall_manager

manager = get_firewall_manager()

if manager.blocked_ips:
    print(f"   Removing {len(manager.blocked_ips)} blocked IPs...")
    for ip in list(manager.blocked_ips):
        manager.unblock_ip(ip)
    print("   ✅ All blocks removed!")
else:
    print("   No blocked IPs found")
PYEOF

echo ""
echo "📋 Current FORWARD chain:"
sudo iptables -L FORWARD -n -v --line-numbers | head -10
echo ""
echo "✅ Cleanup complete!"
