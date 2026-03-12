#!/usr/bin/env python3
"""
DNS-based Web Filtering Manager
Manages domain blocking via dnsmasq for reliable web filtering
"""

import subprocess
import logging
import os
import tempfile
from typing import List, Set, Optional
from db import web_filter_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DNSMASQ_BLOCKLIST_FILE = "/etc/dnsmasq.d/blocklist.conf"
DNSMASQ_APPLY_HELPER = os.environ.get("DNSMASQ_APPLY_HELPER", "/usr/local/sbin/wifi-dnsmasq-apply")


def _run_privileged_command(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command with root privileges without interactive sudo prompts."""
    command = args if os.geteuid() == 0 else ["sudo", "-n", *args]
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    if check and result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or f"exit code {result.returncode}"
        raise RuntimeError(f"Command failed: {' '.join(command)} :: {detail}")

    return result


def _apply_dnsmasq_changes(temp_file: Optional[str] = None, clear: bool = False) -> None:
    """
    Apply dnsmasq changes using privileged helper if available.
    Falls back to direct root commands when helper is unavailable.
    """
    helper_exists = os.path.exists(DNSMASQ_APPLY_HELPER) and os.access(DNSMASQ_APPLY_HELPER, os.X_OK)

    if helper_exists:
        helper_args = [DNSMASQ_APPLY_HELPER, "--clear"] if clear else [DNSMASQ_APPLY_HELPER, str(temp_file or "")]
        _run_privileged_command(helper_args, check=True)
        return

    if clear:
        _run_privileged_command(["rm", "-f", DNSMASQ_BLOCKLIST_FILE], check=False)
        _run_privileged_command(["systemctl", "restart", "dnsmasq"], check=True)
        return

    if not temp_file:
        raise RuntimeError("Temporary blocklist file path is required")

    _run_privileged_command([
        "install", "-o", "root", "-g", "root", "-m", "0644", temp_file, DNSMASQ_BLOCKLIST_FILE
    ], check=True)
    _run_privileged_command(["systemctl", "restart", "dnsmasq"], check=True)

def get_blocked_domains() -> Set[str]:
    """Get all domains that should be blocked from MongoDB"""
    try:
        config = web_filter_collection.find_one({"type": "config"})
        if not config:
            logger.warning("No filter configuration found")
            return set()
        
        domains = set()
        
        # Add manually blocked sites
        if "manual_blocks" in config:
            domains.update(config["manual_blocks"])
        
        # Add active category sites
        if "categories" in config:
            for category, details in config["categories"].items():
                if details.get("active", False):
                    domains.update(details.get("sites", []))
        
        logger.info(f"Found {len(domains)} domains to block")
        return domains
        
    except Exception as e:
        logger.error(f"Error getting blocked domains: {e}")
        return set()


def update_dnsmasq_blocklist():
    """Update dnsmasq blocklist configuration file"""
    temp_file = None
    try:
        domains = get_blocked_domains()
        
        if not domains:
            logger.info("No domains to block, removing blocklist file")
            _apply_dnsmasq_changes(clear=True)
            return True
        
        # Generate blocklist configuration
        config_lines = [
            "# Auto-generated web filtering blocklist",
            "# DO NOT EDIT MANUALLY - managed by WiFi Management System\n"
        ]
        
        for domain in sorted(domains):
            # Clean domain name
            domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
            # Block domain by returning 0.0.0.0 for all queries
            config_lines.append(f"address=/{domain}/0.0.0.0")
        
        # Write to a unique temp file first to avoid permission issues
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('\n'.join(config_lines))
            temp_file = f.name

        logger.info("Applying dnsmasq blocklist...")
        _apply_dnsmasq_changes(temp_file=temp_file, clear=False)
        
        logger.info(f"✅ Blocked {len(domains)} domains via DNS")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update dnsmasq blocklist: {e}")
        return False
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def test_domain_blocked(domain: str) -> bool:
    """Test if a domain is successfully blocked"""
    try:
        result = subprocess.run(
            ['nslookup', domain, '192.168.50.1'],
            capture_output=True,
            text=True,
            timeout=5
        )
        # If DNS returns 0.0.0.0, domain is blocked
        return '0.0.0.0' in result.stdout
    except Exception as e:
        logger.error(f"Error testing domain {domain}: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        print("Testing DNS-based blocking...")
        update_dnsmasq_blocklist()
        
        print("\nTesting ea.com blocking...")
        if test_domain_blocked("ea.com"):
            print("✅ ea.com is blocked")
        else:
            print("❌ ea.com is NOT blocked")
    else:
        # Normal update mode
        update_dnsmasq_blocklist()
