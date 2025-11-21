import requests
from requests_oauthlib import OAuth1
from typing import Dict, Any, Optional


class Magento2Client:
    """
    Lightweight wrapper for Magento 2 REST API
    Supports products, orders, and connectivity verification.
    """

    def __init__(
        self,
        store_url: str,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
        api_version: str = "V1"
    ):
        """
        Initialize Magento Client.

        :param store_url: Base Magento store URL (example: https://mystore.com)
        :param consumer_key: Magento Consumer Key
        :param consumer_secret: Magento Consumer Secret
        :param access_token: OAuth token
        :param access_token_secret: OAuth token secret
        :param api_version: Magento REST API version (default: V1)
        """
        self.store_url = store_url.rstrip("/")  # remove trailing slash
        self.api_base = f"{self.store_url}/rest/{api_version}"
        
        self.auth = OAuth1(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
            signature_type="auth_header"
        )
        
        self.headers = {"Content-Type": "application/json"}

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.api_base}{endpoint}"
        res = requests.get(url, auth=self.auth, headers=self.headers, params=params)
        res.raise_for_status()
        return res.json()

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_base}{endpoint}"
        res = requests.post(url, auth=self.auth, headers=self.headers, json=data)
        res.raise_for_status()
        return res.json()

    # ------------ Products ------------

    def list_products(self, page_size: int = 50, current_page: int = 1) -> Dict[str, Any]:
        """Fetch product list with pagination"""
        params = {
            "searchCriteria[pageSize]": page_size,
            "searchCriteria[currentPage]": current_page
        }
        return self._get("/products", params=params)

    def get_product(self, sku: str) -> Dict[str, Any]:
        """Fetch product details by SKU"""
        return self._get(f"/products/{sku}")

    def update_product(self, sku: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update product info"""
        payload = {"product": update_data}
        return self._post(f"/products/{sku}", payload)

    # ------------ Orders ------------

    def list_orders(self, page_size: int = 50, current_page: int = 1) -> Dict[str, Any]:
        """Fetch orders"""
        params = {
            "searchCriteria[pageSize]": page_size,
            "searchCriteria[currentPage]": current_page
        }
        return self._get("/orders", params=params)

    def get_order(self, order_id: int) -> Dict[str, Any]:
        """Fetch a single order by ID"""
        return self._get(f"/orders/{order_id}")

    # ------------ Connection Test ------------

    def test_connection(self) -> bool:
        """Basic test to verify integration"""
        try:
            self.list_products(page_size=1)
            return True
        except Exception:
            return False
