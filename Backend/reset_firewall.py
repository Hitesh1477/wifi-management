import sys
sys.path.insert(0, '/home/nikhil/wifi-management/Backend')
from linux_firewall_manager import get_firewall_manager, setup_captive_portal
from db import db

def full_reset():
    print("🔄 Starting detailed firewall reset...")
    manager = get_firewall_manager()
    
    # 1. Full Reset
    print("1. Flushing all rules...")
    manager.reset_firewall()
    
    # 2. Setup Base Portal
    print("2. Setting up captive portal (with redirection)...")
    setup_captive_portal()
    
    # 3. Re-allow Valid Sessions
    print("3. Syncing active sessions...")
    active_sessions = list(db.active_sessions.find({'status': 'active'}))
    print(f"   Found {len(active_sessions)} active sessions")
    
    for session in active_sessions:
        ip = session.get('client_ip')
        if ip and ip.startswith('192.168.50.'):
            # Only re-allow if we can ping them? No, just trust DB for now
            # session_cleanup.py handles the ping check
            from linux_firewall_manager import allow_authenticated_user
            allow_authenticated_user(ip)
            
    print("✅ Firewall Reset Complete!")

if __name__ == "__main__":
    full_reset()
