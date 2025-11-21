import requests
from typing import Dict, Any, Optional


class QaplaClient:
    """
    Lightweight Python client for Qapla Ecommerce API.
    Supports products, orders, and connectivity verification.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.qapla.it/v1"):
        """
        Initialize the Qapla client.

        :param api_key: Qapla API Key
        :param base_url: Qapla API base URL
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
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

    def list_products(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Fetch a list of products"""
        params = {"page": page, "per_page": per_page}
        return self._get("/products", params=params)

    def get_product(self, product_id: str) -> Dict[str, Any]:
        """Fetch a single product by ID"""
        return self._get(f"/products/{product_id}")

    # ------------- Orders -------------

    def list_orders(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Fetch a list of orders"""
        params = {"page": page, "per_page": per_page}
        return self._get("/orders", params=params)

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Fetch a single order by ID"""
        return self._get(f"/orders/{order_id}")

    # ------------- Connection Test -------------

    def test_connection(self) -> bool:
        """Simple connectivity test"""
        try:
            self.list_products(page=1, per_page=1)
            return True
        except Exception:
            return False
