#!/bin/bash
# Test script for real-time web filtering
# This demonstrates blocking instagram.com for authenticated users

echo "🧪 Testing Real-Time Web Filtering"
echo "=================================="
echo ""

cd "$(dirname "$0")"

echo "📋 Step 1: Current FORWARD chain rules"
sudo iptables -L FORWARD -n -v --line-numbers | head -20
echo ""

echo "📋 Step 2: Testing with instagram.com"
echo "   Adding instagram.com to blocked list..."
python3 <<'PYEOF'
import sys
sys.path.insert(0, '/home/nikhil/wifi-management/Backend')

from linux_firewall_manager import get_firewall_manager

manager = get_firewall_manager()

# Block instagram.com
print("   Resolving instagram.com IPs...")
ips = manager.resolve_domain_ips("instagram.com")
print(f"   Found {len(ips)} IP addresses: {ips}")

print("   Blocking IPs...")
for ip in ips:
    manager.block_ip(ip)

print("   ✅ instagram.com blocked!")
PYEOF

echo ""
echo "📋 Step 3: Updated FORWARD chain rules"
echo "   DROP rules should now be at the TOP (positions 1-N)"
sudo iptables -L FORWARD -n -v --line-numbers | head -20
echo ""

echo "=================================="
echo "✅ Test Complete!"
echo "=================================="
echo ""
echo "🎯 Expected behavior:"
echo "   - DROP rules for Instagram IPs should be at positions 1-5"
echo "   - Authenticated user ACCEPT rules should be at positions 100+"
echo "   - Instagram should now be blocked for ALL users"
echo ""
echo "🧪 To test:"
echo "   1. Try accessing instagram.com from connected device"
echo "   2. Should be blocked/timeout"
echo ""
echo "🧹 To cleanup (remove instagram block):"
echo "   python3 -c \"from linux_firewall_manager import get_firewall_manager; m = get_firewall_manager(); [m.unblock_ip(ip) for ip in m.blocked_ips.copy()]\""
