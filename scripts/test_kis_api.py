"""
Quick test - Korea Investment Securities API connectivity
"""
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")

print("=" * 60)
print("🔑 KIS API Configuration Check")
print("=" * 60)

if not KIS_APP_KEY or KIS_APP_KEY == "":
    print("❌ KIS_APP_KEY not found in .env file")
    print("\n📝 How to get KIS API KEY:")
    print("   1. Visit: https://apiportal.koreainvestment.com")
    print("   2. Sign up with Korea Investment account")
    print("   3. Register new app")
    print("   4. Copy APP KEY and APP SECRET to .env")
    exit(1)

if not KIS_APP_SECRET or KIS_APP_SECRET == "":
    print("❌ KIS_APP_SECRET not found in .env file")
    exit(1)

print(f"✅ KIS_APP_KEY found: {KIS_APP_KEY[:10]}...")
print(f"✅ KIS_APP_SECRET found: {KIS_APP_SECRET[:10]}...")

# Test API connection
try:
    from pykis import PyKis

    print("\n📊 Testing KIS API connection...")

    # Initialize (this will validate credentials)
    kis = PyKis()

    print("✅ KIS API initialized successfully!")

    # Test with Samsung Electronics
    print("\n🔍 Testing stock quote retrieval (005930)...")
    stock = kis.stock("005930")
    quote = stock.quote()

    if quote:
        print("✅ Stock quote retrieved successfully!")
        print(f"   종목명: {quote.get('hts_kor_isnm', 'N/A')}")
        print(f"   현재가: {int(quote.get('stck_prpr', 0)):,}원")
        print(f"   등락률: {float(quote.get('prdy_ctrt', 0))}%")
    else:
        print("❌ Could not retrieve stock quote")

except ImportError:
    print("\n⚠️  pykis library not installed")
    print("   Install: pip install pykis")
    exit(1)

except Exception as e:
    print(f"\n❌ KIS API test failed: {e}")
    print("\n💡 Possible issues:")
    print("   - Invalid APP KEY or APP SECRET")
    print("   - API permissions not granted")
    print("   - Network connection issue")
    exit(1)

print("\n" + "=" * 60)
print("✅ KIS API test completed successfully!")
print("=" * 60)
