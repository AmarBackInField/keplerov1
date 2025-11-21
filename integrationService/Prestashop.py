import requests
from typing import Dict, Any, Optional
from requests.auth import HTTPBasicAuth


class PrestashopClient:
    """
    Lightweight Python client for Prestashop API.
    Supports products, orders, and connection verification.
    """

    def __init__(self, store_url: str, api_key: str, api_version: str = "api"):
        """
        Initialize Prestashop Client.

        :param store_url: Base store URL (example: https://mystore.com)
        :param api_key: Prestashop API key
        :param api_version: API endpoint version (default: "api")
        """
        self.store_url = store_url.rstrip("/")
        self.api_base = f"{self.store_url}/{api_version}"
        self.api_key = api_key

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.api_base}/{endpoint}"
        response = requests.get(url, auth=HTTPBasicAuth(self.api_key, ""), params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_base}/{endpoint}"
        response = requests.post(url, auth=HTTPBasicAuth(self.api_key, ""), json=data)
        response.raise_for_status()
        return response.json()

    # ------------- Products -------------

    def list_products(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Fetch list of products"""
        params = {"display": "full", "limit": f"{offset},{limit}"}
        return self._get("products", params=params)

    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Fetch single product by ID"""
        return self._get(f"products/{product_id}")

    # ------------- Orders -------------

    def list_orders(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Fetch list of orders"""
        params = {"display": "full", "limit": f"{offset},{limit}"}
        return self._get("orders", params=params)

    def get_order(self, order_id: int) -> Dict[str, Any]:
        """Fetch single order by ID"""
        return self._get(f"orders/{order_id}")

    # ------------- Connection Test -------------

    def test_connection(self) -> bool:
        """Verify connectivity with the store"""
        try:
            self.list_products(limit=1)
            return True
        except Exception:
            return False
