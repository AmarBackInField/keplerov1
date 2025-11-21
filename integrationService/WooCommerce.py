import requests
from typing import Dict, Any, Optional


class WooCommerceClient:
    """
    Lightweight wrapper for WooCommerce REST API
    Suitable for Kepler AI Ecommerce integration.
    """

    def __init__(
        self,
        store_url: str,
        consumer_key: str,
        consumer_secret: str,
        api_version: str = "wc/v3"
    ):
        """
        Initialize WooCommerce Client.

        :param store_url: Base store URL (example: https://mystore.com)
        :param consumer_key: WooCommerce Consumer Key
        :param consumer_secret: WooCommerce Consumer Secret
        :param api_version: REST API version (default: wc/v3)
        """
        self.store_url = store_url.rstrip("/")
        self.api_base = f"{self.store_url}/wp-json/{api_version}"
        self.auth = (consumer_key, consumer_secret)
        self.headers = {"Content-Type": "application/json"}

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.api_base}{endpoint}"
        response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_base}{endpoint}"
        response = requests.post(url, auth=self.auth, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    # ------------- Products -------------

    def list_products(self, per_page: int = 50) -> Dict[str, Any]:
        """Fetch list of products"""
        return self._get("/products", params={"per_page": per_page})

    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Get details of a single product"""
        return self._get(f"/products/{product_id}")

    def update_product(self, product_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update product"""
        return self._post(f"/products/{product_id}", update_data)

    # ------------- Orders -------------

    def list_orders(self, per_page: int = 50) -> Dict[str, Any]:
        """Fetch order list"""
        return self._get("/orders", params={"per_page": per_page})

    def get_order(self, order_id: int) -> Dict[str, Any]:
        """Get details of a single order"""
        return self._get(f"/orders/{order_id}")

    # ------------- Connection Test -------------

    def test_connection(self) -> bool:
        """Simple test request"""
        try:
            self.list_products(per_page=1)
            return True
        except Exception:
            return False
