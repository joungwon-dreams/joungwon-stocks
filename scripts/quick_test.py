"""
Quick test - DART API connectivity
"""
import dart_fss as dart
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY")

if not DART_API_KEY:
    print("❌ DART_API_KEY not found in .env file")
    exit(1)

print(f"✅ DART_API_KEY loaded: {DART_API_KEY[:10]}...")

# Set API key
dart.set_api_key(DART_API_KEY)

try:
    # Test API connection
    print("\n📊 Testing DART API connection...")
    corp_list = dart.get_corp_list()

    # Find Samsung Electronics
    corp = corp_list.find_by_stock_code("005930")

    if corp:
        print(f"✅ DART API connected successfully!")
        print(f"   Company: {corp.corp_name}")
        print(f"   Stock Code: {corp.stock_code}")
        print(f"   Corp Code: {corp.corp_code}")
    else:
        print("❌ Could not find Samsung Electronics (005930)")

except Exception as e:
    print(f"❌ DART API test failed: {e}")
    exit(1)

print("\n" + "="*60)
print("✅ Quick test completed successfully!")
print("="*60)
