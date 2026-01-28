"""
IP Refresh Service
Periodically refreshes IP addresses for blocked domains and updates firewall rules
Run this script every 6 hours using Windows Task Scheduler
"""

import sys
import datetime
from pymongo import MongoClient
from domain_resolver import resolve_multiple_domains
from firewall_blocker import block_domain, unblock_domain, get_firewall_stats


# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']
web_filter_collection = db['web_filter']
firewall_rules_collection = db['firewall_rules']
refresh_log_collection = db['firewall_refresh_log']


def get_blocked_domains_from_config():
    """
    Get all blocked domains from web_filter configuration.
    
    Returns:
        List of domain names
    """
    try:
        config = web_filter_collection.find_one({"type": "config"})
        if not config:
            return []
        
        blocked = []
        
        # Add manually blocked sites
        manual_blocks = config.get("manual_blocks", [])
        if isinstance(manual_blocks, list):
            for domain in manual_blocks:
                if isinstance(domain, str):
                    blocked.append(domain.lower().strip())
        
        # Add category-blocked sites
        categories = config.get("categories", {})
        for category, data in categories.items():
            if isinstance(data, dict) and data.get("active", False):
                sites = data.get("sites", [])
                for site in sites:
                    if isinstance(site, str):
                        blocked.append(site.lower().strip())
        
        # Remove duplicates
        return list(set(blocked))
    
    except Exception as e:
        print(f"❌ Error loading blocked domains: {e}")
        return []


def refresh_all_firewall_rules():
    """
    Main function: Refresh firewall rules for all blocked domains.
    
    Process:
    1. Load blocked domains from MongoDB
    2. Resolve each domain to current IPs
    3. Compare with existing firewall rules
    4. Update rules if IPs have changed
    """
    print("\n" + "="*60)
    print("🔄 Firewall Rules Refresh Service")
    print("="*60)
    print(f"Started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get blocked domains from configuration
    blocked_domains = get_blocked_domains_from_config()
    
    if not blocked_domains:
        print("\n⚠️  No blocked domains found in configuration")
        return
    
    print(f"\n📋 Found {len(blocked_domains)} blocked domains:")
    for domain in blocked_domains:
        print(f"  - {domain}")
    
    # Resolve all domains to IPs
    print("\n" + "="*60)
    domain_ips = resolve_multiple_domains(blocked_domains)
    
    # Track statistics
    stats = {
        "domains_processed": 0,
        "domains_updated": 0,
        "domains_unchanged": 0,
        "domains_failed": 0,
        "total_rules_created": 0,
        "errors": []
    }
    
    # Update firewall rules for each domain
    print("\n" + "="*60)
    print("🔄 Updating Firewall Rules")
    print("="*60)
    
    for domain, new_ips in domain_ips.items():
        stats["domains_processed"] += 1
        
        if not new_ips:
            print(f"\n⚠️  {domain}: No IPs found, skipping")
            stats["domains_failed"] += 1
            stats["errors"].append(f"{domain}: No IPs resolved")
            continue
        
        # Get existing IPs from MongoDB
        existing_rule = firewall_rules_collection.find_one({"domain": domain})
        existing_ips = set(existing_rule.get("ips", [])) if existing_rule else set()
        
        # Compare IPs
        if existing_ips == new_ips:
            print(f"\n✅ {domain}: IPs unchanged ({len(new_ips)} IPs)")
            stats["domains_unchanged"] += 1
        else:
            print(f"\n🔄 {domain}: IPs changed")
            print(f"  Old IPs: {len(existing_ips)}")
            print(f"  New IPs: {len(new_ips)}")
            
            # Remove old rules
            if existing_ips:
                unblock_domain(domain)
            
            # Create new rules
            success, msg, count = block_domain(domain, new_ips)
            
            if success:
                stats["domains_updated"] += 1
                stats["total_rules_created"] += count
                print(f"  ✅ Updated: {msg}")
            else:
                stats["domains_failed"] += 1
                stats["errors"].append(f"{domain}: {msg}")
                print(f"  ❌ Failed: {msg}")
    
    # Log this refresh cycle
    try:
        refresh_log_collection.insert_one({
            "timestamp": datetime.datetime.utcnow(),
            "stats": stats,
            "blocked_domains": blocked_domains
        })
    except Exception as e:
        print(f"\n⚠️  Could not log refresh cycle: {e}")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Refresh Summary")
    print("="*60)
    print(f"Domains processed: {stats['domains_processed']}")
    print(f"Domains updated: {stats['domains_updated']}")
    print(f"Domains unchanged: {stats['domains_unchanged']}")
    print(f"Domains failed: {stats['domains_failed']}")
    print(f"Total rules created: {stats['total_rules_created']}")
    
    if stats["errors"]:
        print(f"\nErrors:")
        for error in stats["errors"]:
            print(f"  ❌ {error}")
    
    # Show current firewall stats
    firewall_stats = get_firewall_stats()
    print(f"\n📊 Current Firewall Status:")
    print(f"Total blocked domains: {firewall_stats.get('blocked_domains', 0)}")
    print(f"Total firewall rules: {firewall_stats.get('total_firewall_rules', 0)}")
    
    print(f"\n✅ Refresh complete at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


if __name__ == "__main__":
    try:
        refresh_all_firewall_rules()
    except KeyboardInterrupt:
        print("\n\n⏹️  Refresh interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
