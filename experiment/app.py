import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# BASE_URL = os.getenv("WC_BASE_URL")
# CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
# CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")
BASE_URL = "https://www.aistein.it/wp-json/wc/v3"

CONSUMER_KEY = "ck_8389e39269997a489f20582a7fe9a02d57e242e6"
CONSUMER_SECRET = "cs_8adb1d49dfac66213a340e6184c4df19c1b7484e"

auth = HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET)
headers = {
    "Content-Type": "application/json"
}

def test_connection():
    print("\n🔍 Testing WooCommerce API connection...")
    url = f"{BASE_URL}/products"
    response = requests.get(url, auth=auth)

    if response.status_code == 200:
        print("✅ Connection successful!")
    else:
        print("❌ Connection failed")
        print(response.status_code, response.text)
        exit(1)

def get_products(limit=5):
    print("\n📦 Fetching products...")
    url = f"{BASE_URL}/products"
    params = {"per_page": limit}
    response = requests.get(url, auth=auth, params=params)

    if response.status_code == 200:
        products = response.json()
        print(f"✅ Found {len(products)} products")
        for p in products:
            print(f"- {p['id']} | {p['name']} | ₹{p['price']} | {p['description']}")
        
        # Save to JSON file
        with open('products.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        print("💾 Products saved to products.json")
    else:
        print("❌ Failed to fetch products")
        print(response.status_code, response.text)

def get_all_products():
    print("\n📦 Fetching ALL products...")
    url = f"{BASE_URL}/products"
    all_products = []
    page = 1
    per_page = 100  # Maximum allowed by WooCommerce
    
    while True:
        params = {"per_page": per_page, "page": page}
        response = requests.get(url, auth=auth, params=params)
        
        if response.status_code == 200:
            products = response.json()
            
            if not products:  # No more products
                break
                
            all_products.extend(products)
            print(f"📄 Page {page}: Fetched {len(products)} products (Total: {len(all_products)})")
            page += 1
        else:
            print(f"❌ Failed to fetch products on page {page}")
            print(response.status_code, response.text)
            break
    
    if all_products:
        print(f"\n✅ Total products fetched: {len(all_products)}")
        
        # Save to JSON file
        with open('all_products.json', 'w', encoding='utf-8') as f:
            json.dump(all_products, f, indent=2, ensure_ascii=False)
        print("💾 All products saved to all_products.json")
        
        # Display sample products
        print("\n📋 Sample products:")
        for p in all_products[:5]:
            print(f"- {p['id']} | {p['name']} | ₹{p['price']}")
        if len(all_products) > 5:
            print(f"... and {len(all_products) - 5} more")
    
    return all_products

def get_orders(limit=5):
    print("\n🧾 Fetching orders...")
    url = f"{BASE_URL}/orders"
    params = {"per_page": limit}
    response = requests.get(url, auth=auth, params=params)

    if response.status_code == 200:
        orders = response.json()
        print(f"✅ Found {len(orders)} orders")
        for o in orders:
            print(f"- Order #{o['id']} | Status: {o['status']} | Total: ₹{o['total']}")
        
        # Save to JSON file
        with open('orders.json', 'w', encoding='utf-8') as f:
            json.dump(orders, f, indent=2, ensure_ascii=False)
        print("💾 Orders saved to orders.json")
    else:
        print("❌ Failed to fetch orders")
        print(response.status_code, response.text)

def create_test_product():
    print("\n🧪 Creating test product...")
    url = f"{BASE_URL}/products"
    payload = {
        "name": "API Test Product",
        "type": "simple",
        "regular_price": "199",
        "description": "Created via WooCommerce REST API",
        "short_description": "API test product",
        "categories": [{"id": 1}]
    }

    response = requests.post(url, auth=auth, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        product = response.json()
        # NUMBER OF PRODUCTS
        print(f"Number of products: {len(product)}")
        print("✅ Product created successfully")
        print(f"ID: {product['id']} | Name: {product['name']}")
    else:
        print("❌ Failed to create product")
        print(response.status_code, response.text)

if __name__ == "__main__":
    print("🚀 WooCommerce API Full Test Script")

    test_connection()
    get_products()
    get_orders()
    
    # Fetch all products (with pagination)
    get_all_products()

    # ⚠️ Enable ONLY if you want to create a product
    # create_test_product()

    print("\n🎉 All tests completed!")
