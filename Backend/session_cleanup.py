#!/usr/bin/env python3
"""
Session Cleanup Service
Automatically detects and removes stale sessions from disconnected users
Run this periodically (e.g., every 5 minutes via cron)
"""

import subprocess
import sys
import logging
import os
from datetime import datetime
import ipaddress

# Add backend to path
sys.path.insert(0, '/home/nikhil/wifi-management/Backend')
from db import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def _safe_non_negative_int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _is_hotspot_client_ip(client_ip: str) -> bool:
    subnet = os.environ.get('HOTSPOT_SUBNET', '192.168.50.0/24')
    try:
        return ipaddress.ip_address(client_ip) in ipaddress.ip_network(subnet, strict=False)
    except Exception:
        return False


def _persist_session_usage(session):
    roll_no = str(session.get('roll_no') or '').strip()
    client_ip = str(session.get('client_ip') or '').strip()
    if not roll_no or not client_ip:
        return

    try:
        from linux_firewall_manager import get_usage_for_client_ip

        usage = get_usage_for_client_ip(client_ip) or {}
    except Exception as error:
        logger.warning("Failed to read usage counters for %s (%s): %s", roll_no, client_ip, error)
        return

    current_upload = _safe_non_negative_int(usage.get('upload_bytes'))
    current_download = _safe_non_negative_int(usage.get('download_bytes'))

    accounted_upload = _safe_non_negative_int(session.get('usage_accounted_upload_bytes'))
    accounted_download = _safe_non_negative_int(session.get('usage_accounted_download_bytes'))

    delta_upload = current_upload - accounted_upload if current_upload >= accounted_upload else current_upload
    delta_download = current_download - accounted_download if current_download >= accounted_download else current_download
    delta_total = max(0, delta_upload + delta_download)

    if delta_total > 0:
        db['users'].update_one(
            {'roll_no': roll_no},
            {
                '$inc': {
                    'total_data_bytes': delta_total,
                    'total_upload_bytes': max(0, delta_upload),
                    'total_download_bytes': max(0, delta_download),
                },
                '$set': {'data_usage_updated_at': datetime.utcnow()},
            },
        )

    db['active_sessions'].update_one(
        {'_id': session['_id']},
        {
            '$set': {
                'usage_upload_bytes': current_upload,
                'usage_download_bytes': current_download,
                'usage_total_bytes': current_upload + current_download,
                'usage_accounted_upload_bytes': current_upload,
                'usage_accounted_download_bytes': current_download,
                'usage_last_sync': datetime.utcnow(),
            }
        },
    )

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
                try:
                    _persist_session_usage(session)
                except Exception as usage_error:
                    logger.warning("Failed to persist usage for %s (%s): %s", roll_no, client_ip, usage_error)

                if _is_hotspot_client_ip(client_ip):
                    try:
                        from linux_firewall_manager import block_authenticated_user

                        block_authenticated_user(client_ip)
                    except Exception as firewall_error:
                        logger.warning(
                            "Failed to revoke firewall access for stale session %s (%s): %s",
                            roll_no,
                            client_ip,
                            firewall_error,
                        )

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
