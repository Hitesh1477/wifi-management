#!/usr/bin/env python3
"""
Session Cleanup Service
Automatically detects and removes stale sessions from disconnected users
Run this periodically (e.g., every 5 minutes via cron)
"""

import subprocess
import sys
import logging
from datetime import datetime

# Add backend to path
sys.path.insert(0, '/home/nikhil/wifi-management/Backend')
from db import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def is_ip_reachable(ip: str, timeout: int = 1) -> bool:
    """Check if an IP is reachable via ping"""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), ip],
            capture_output=True,
            timeout=timeout + 1
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def cleanup_stale_sessions():
    """Find and deactivate sessions for disconnected users"""
    try:
        active_sessions_col = db['active_sessions']
        
        # Get all active sessions
        active_sessions = list(active_sessions_col.find({'status': 'active'}))
        
        if not active_sessions:
            logger.info("No active sessions to check")
            return
        
        logger.info(f"Checking {len(active_sessions)} active session(s)...")
        
        cleaned_count = 0
        still_active = []
        
        for session in active_sessions:
            roll_no = session.get('roll_no', 'Unknown')
            client_ip = session.get('client_ip', 'N/A')
            
            # Skip if no IP
            if not client_ip or client_ip == 'N/A':
                continue
            
            # Check if device is still connected
            if is_ip_reachable(client_ip):
                still_active.append(f"{roll_no} ({client_ip})")
            else:
                # Device disconnected - mark session as inactive
                active_sessions_col.update_one(
                    {'_id': session['_id']},
                    {
                        '$set': {
                            'status': 'inactive',
                            'logout_time': datetime.utcnow(),
                            'auto_cleanup': True
                        }
                    }
                )
                cleaned_count += 1
                logger.info(f"❌ Cleaned up stale session: {roll_no} ({client_ip})")
        
        # Summary
        if cleaned_count > 0:
            logger.info(f"✅ Cleaned up {cleaned_count} stale session(s)")
        
        if still_active:
            logger.info(f"✅ {len(still_active)} user(s) still connected: {', '.join(still_active)}")
        
        if cleaned_count == 0 and len(still_active) == 0:
            logger.info("✅ All sessions are valid")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Session Cleanup Service - Starting")
    logger.info("=" * 60)
    cleanup_stale_sessions()
    logger.info("=" * 60)
    logger.info("Session Cleanup Service - Completed")
    logger.info("=" * 60)
