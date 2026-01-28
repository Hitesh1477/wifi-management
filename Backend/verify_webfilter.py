"""
Quick script to verify and test web_filter collection setup
"""

from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']
web_filter_collection = db['web_filter']

# Check if collection exists and show config
config = web_filter_collection.find_one({"type": "config"})

if config:
    print("✅ web_filter collection exists!")
    print(f"\n📋 Categories ({len(config['categories'])}):")
    for cat_name, cat_data in config['categories'].items():
        status = "✅ Active" if cat_data.get('active') else "⏸️  Inactive"
        print(f"   {status} {cat_name}: {len(cat_data.get('sites', []))} sites")
    
    print(f"\n🚫 Manual blocks ({len(config['manual_blocks'])}):")
    for site in config['manual_blocks']:
        print(f"   - {site}")
    
    # Test: Add instagram.com if not already there
    if 'instagram.com' not in config['manual_blocks']:
        print("\n➕ Adding instagram.com to test...")
        web_filter_collection.update_one(
            {"type": "config"},
            {"$push": {"manual_blocks": "instagram.com"}}
        )
        print("✅ Instagram added to blocked list!")
        print("\nNow trigger firewall rules by running:")
        print("  python -c \"from firewall_blocker import block_domain; from domain_resolver import resolve_domain_to_ips; ips = resolve_domain_to_ips('instagram.com'); block_domain('instagram.com', ips)\"")
    else:
        print("\nℹ️  instagram.com is already in the blocked list")

else:
    print("❌ web_filter collection not found!")
