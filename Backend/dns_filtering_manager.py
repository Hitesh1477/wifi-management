#!/usr/bin/env python3
"""
DNS-based Web Filtering Manager
Manages domain blocking via dnsmasq for reliable web filtering
"""

import subprocess
import logging
from typing import List, Set
from db import web_filter_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DNSMASQ_BLOCKLIST_FILE = "/etc/dnsmasq.d/blocklist.conf"

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
    try:
        domains = get_blocked_domains()
        
        if not domains:
            logger.info("No domains to block, removing blocklist file")
            subprocess.run(['sudo', 'rm', '-f', DNSMASQ_BLOCKLIST_FILE], check=False)
            subprocess.run(['sudo', 'systemctl', 'restart', 'dnsmasq'], check=True)
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
        
        import tempfile
        import os
        
        # Write to a unique temp file first to avoid permission issues
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('\n'.join(config_lines))
            temp_file = f.name
        
        # Move to dnsmasq config directory
        subprocess.run([
            'sudo', 'mv', temp_file, DNSMASQ_BLOCKLIST_FILE
        ], check=True)

        
        # Set proper permissions
        subprocess.run([
            'sudo', 'chmod', '644', DNSMASQ_BLOCKLIST_FILE
        ], check=True)
        
        # Restart dnsmasq to apply changes
        logger.info("Restarting dnsmasq to apply blocklist...")
        subprocess.run(['sudo', 'systemctl', 'restart', 'dnsmasq'], check=True)
        
        logger.info(f"✅ Blocked {len(domains)} domains via DNS")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update dnsmasq blocklist: {e}")
        return False


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
