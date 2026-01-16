# import requests

# BASE_URL = "https://aistein.it/wp-json/wc/v3"
# CONSUMER_KEY = "ck_8389e39269997a489f20582a7fe9a02d57e242e6"
# CONSUMER_SECRET = "cs_8adb1d49dfac66213a340e6184c4df19c1b7484e"

# url = f"{BASE_URL}/orders"
import requests
import json

# BASE_URL = "https://aistein.it/wp-json/wc/v3"
BASE_URL = "https://www.aistein.it/wp-json/wc/v3"

CK = "ck_8389e39269997a489f20582a7fe9a02d57e242e6"
CS = "cs_8adb1d49dfac66213a340e6184c4df19c1b7484e"

r = requests.get(
    f"{BASE_URL}/orders",
    auth=(CK, CS),
    timeout=10
)

print("Status:", r.status_code)
with open("orders.json", "w") as f:
    f.write(json.dumps(r.json(), indent=4))
