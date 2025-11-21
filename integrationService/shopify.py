import requests
from typing import Dict, Any, Optional

class ShopifyClient:
    """
    A lightweight Python wrapper to interact with Shopify Admin REST API.
    Handles authentication + product & order operations.
    """
    
    def __init__(self, shop_url: str, admin_api_key: str, api_version: str = "2024-10"):
        """
        Initialize the Shopify Client.

        :param shop_url: Shopify Store URL (e.g. amar-store.myshopify.com)
        :param admin_api_key: Admin API Access Token (Private app token)
        :param api_version: Shopify API version
        """
        self.base_url = f"https://{shop_url}/admin/api/{api_version}"
        self.headers = {
            "X-Shopify-Access-Token": admin_api_key,
            "Content-Type": "application/json"
        }

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    # ------------- Products -------------
    
    def get_all_products(self, limit: int = 50) -> Dict[str, Any]:
        """Fetch list of products"""
        return self._get("/products.json", params={"limit": limit})

    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Fetch product details by ID"""
        return self._get(f"/products/{product_id}.json")

    def update_product(self, product_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update product details"""
        payload = {"product": update_data}
        return self._post(f"/products/{product_id}.json", payload)

    # ------------- Orders -------------
    
    def get_all_orders(self, limit: int = 50) -> Dict[str, Any]:
        """Fetch list of recent orders"""
        return self._get("/orders.json", params={"limit": limit})

    def get_order(self, order_id: int) -> Dict[str, Any]:
        """Fetch single order by ID"""
        return self._get(f"/orders/{order_id}.json")

    # ------------- Admin Status Test -------------
    
    def test_connection(self) -> bool:
        """Verify Shopify API connectivity"""
        try:
            self.get_all_products(limit=1)
            return True
        except Exception:
            return False
