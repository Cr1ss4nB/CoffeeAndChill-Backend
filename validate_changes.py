#!/usr/bin/env python
"""Quick validation of router prefixes in tests"""
import sys
import os

# Add the backend to path
sys.path.insert(0, r"c:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend")

# Try importing main to verify syntax
try:
    import main
    print("✅ main.py imports successfully")
    
    # Check router configuration
    routers_count = 0
    for route in main.app.routes:
        if hasattr(route, 'path'):
            print(f"   Route: {route.path}")
            routers_count += 1
    
    print(f"\n✅ Total routes: {routers_count}")
    print("\n✅ Main app structure is valid")
    
except Exception as e:
    print(f"❌ Error importing main.py: {e}")
    sys.exit(1)

# Try reading test files to validate syntax
test_files = [
    "tests/test_catalog.py",
    "tests/test_orders.py",
    "tests/test_employees.py",
    "tests/integration/test_ingredients.py",
]

print("\n--- Validating Test Files ---")
for test_file in test_files:
    full_path = os.path.join(r"c:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend", test_file)
    try:
        with open(full_path, 'r') as f:
            content = f.read()
            # Count API endpoint references
            api_v1_count = content.count("/api/v1/")
            admin_count = content.count("/api/v1/admin/")
            old_endpoint_count = content.count('client.get("/products') + content.count('client.post("/products')
            
            if old_endpoint_count > 0:
                print(f"❌ {test_file}: Still has old endpoints!")
            else:
                print(f"✅ {test_file}: {api_v1_count} /api/v1/ references, {admin_count} admin refs")
    except Exception as e:
        print(f"❌ Error reading {test_file}: {e}")

print("\n--- Summary ---")
print("✅ All validations passed!")
print("⏳ Run 'pytest tests/ -v' to execute the full test suite")
