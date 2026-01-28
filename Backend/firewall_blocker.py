"""
Firewall Blocker Module
Creates and manages Windows Firewall Forward rules to block hotspot client traffic
"""

import subprocess
import json
from typing import List, Set
from pymongo import MongoClient


# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']
firewall_rules_collection = db['firewall_rules']


def create_firewall_forward_rule(domain: str, ip: str) -> tuple:
    """
    Create a Windows Firewall Forward rule to block an IP for hotspot clients.
    
    Args:
        domain: Domain name (for rule naming)
        ip: IP address to block
    
    Returns:
        (success: bool, message: str)
    """
    # Create unique rule name
    rule_name = f"VDT_Block_{domain.replace('.', '_')}_{ip.replace('.', '_').replace(':', '_')}"
    
    # PowerShell command to create Forward rule
    ps_command = f"""
    New-NetFirewallRule `
        -DisplayName '{rule_name}' `
        -Description 'VDT Web Filter - Block {domain} for hotspot clients' `
        -Direction Outbound `
        -Action Block `
        -RemoteAddress '{ip}' `
        -Protocol TCP `
        -Enabled True `
        -ErrorAction SilentlyContinue
    """
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Check if rule already exists (not an error)
        if "already exists" in result.stderr.lower():
            return True, f"Rule already exists for {ip}"
        
        if result.returncode == 0:
            return True, f"Blocked {ip} for {domain}"
        else:
            return False, f"Failed to create rule: {result.stderr}"
    
    except subprocess.TimeoutExpired:
        return False, "PowerShell timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"


def remove_firewall_forward_rule(rule_name: str) -> tuple:
    """
    Remove a Windows Firewall Forward rule.
    
    Args:
        rule_name: Name of the rule to remove
    
    Returns:
        (success: bool, message: str)
    """
    ps_command = f"Remove-NetFirewallRule -DisplayName '{rule_name}' -ErrorAction SilentlyContinue"
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return True, f"Removed rule: {rule_name}"
    
    except Exception as e:
        return False, f"Error removing rule: {str(e)}"


def block_domain(domain: str, ips: Set[str]) -> tuple:
    """
    Block a domain by creating Forward firewall rules for all its IPs.
    
    Args:
        domain: Domain name to block
        ips: Set of IP addresses for this domain
    
    Returns:
        (success: bool, message: str, rules_created: int)
    """
    if not ips:
        return False, "No IPs provided", 0
    
    print(f"\n🚫 Blocking {domain} ({len(ips)} IPs)...")
    
    rules_created = 0
    failed = 0
    
    for ip in ips:
        success, msg = create_firewall_forward_rule(domain, ip)
        if success:
            rules_created += 1
            print(f"  ✅ {ip}")
        else:
            failed += 1
            print(f"  ❌ {ip}: {msg}")
    
    # Store rule metadata in MongoDB for tracking
    try:
        firewall_rules_collection.update_one(
            {"domain": domain},
            {
                "$set": {
                    "domain": domain,
                    "ips": list(ips),
                    "rules_count": rules_created,
                    "last_updated": datetime.datetime.utcnow()
                }
            },
            upsert=True
        )
    except Exception as e:
        print(f"  ⚠️  Could not save to MongoDB: {e}")
    
    if rules_created > 0:
        return True, f"Blocked {domain} with {rules_created} rules", rules_created
    else:
        return False, f"Failed to create any rules for {domain}", 0


def unblock_domain(domain: str) -> tuple:
    """
    Unblock a domain by removing all its firewall rules.
    
    Args:
        domain: Domain name to unblock
    
    Returns:
        (success: bool, message: str)
    """
    print(f"\n✅ Unblocking {domain}...")
    
    # Find all rules for this domain
    rule_pattern = f"VDT_Block_{domain.replace('.', '_')}_*"
    
    ps_command = f"""
    Get-NetFirewallRule -DisplayName '{rule_pattern}' -ErrorAction SilentlyContinue | 
    Remove-NetFirewallRule -ErrorAction SilentlyContinue
    """
    
    try:
        subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Remove from MongoDB
        firewall_rules_collection.delete_one({"domain": domain})
        
        print(f"  ✅ Removed all rules for {domain}")
        return True, f"Unblocked {domain}"
    
    except Exception as e:
        return False, f"Error unblocking {domain}: {str(e)}"


def list_blocked_domains() -> List[dict]:
    """
    List all currently blocked domains from MongoDB.
    
    Returns:
        List of domain records
    """
    try:
        return list(firewall_rules_collection.find({}, {"_id": 0}))
    except Exception as e:
        print(f"Error listing blocked domains: {e}")
        return []


def get_firewall_stats() -> dict:
    """
    Get statistics about firewall blocking.
    
    Returns:
        Dictionary with stats
    """
    try:
        domains = list(firewall_rules_collection.find())
        total_domains = len(domains)
        total_rules = sum(d.get('rules_count', 0) for d in domains)
        
        return {
            "blocked_domains": total_domains,
            "total_firewall_rules": total_rules,
            "domains": [d['domain'] for d in domains]
        }
    except Exception as e:
        return {"error": str(e)}


import datetime

if __name__ == "__main__":
    # Test the firewall blocker
    from domain_resolver import resolve_domain_to_ips
    
    print("="*60)
    print("Firewall Blocker Test")
    print("="*60)
    
    # Test blocking a domain
    test_domain = "example.com"
    print(f"\nResolving {test_domain}...")
    ips = resolve_domain_to_ips(test_domain)
    
    if ips:
        success, msg, count = block_domain(test_domain, ips)
        print(f"\n{msg}")
        
        # Show stats
        stats = get_firewall_stats()
        print(f"\nFirewall Stats:")
        print(f"  Blocked domains: {stats['blocked_domains']}")
        print(f"  Total rules: {stats['total_firewall_rules']}")
    else:
        print(f"Could not resolve {test_domain}")
