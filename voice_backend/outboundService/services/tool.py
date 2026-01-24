"""
Ecommerce integration tools for voice agents.
Supports WooCommerce, Shopify, and other platforms dynamically.
"""

import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
import aiohttp
from aiohttp import BasicAuth

logger = logging.getLogger("ecommerce_tools")


class EcommerceClient:
    """
    Async client for ecommerce platforms (WooCommerce, Shopify, etc.)
    """
    
    def __init__(
        self, 
        platform: str,
        base_url: str, 
        api_key: str, 
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None
    ):
        """
        Initialize ecommerce client.
        
        Args:
            platform: Platform name ("woocommerce", "shopify", etc.)
            base_url: Base API URL
            api_key: API key / Consumer key
            api_secret: API secret (for WooCommerce)
            access_token: Access token (for Shopify, etc.)
        """
        self.platform = platform.lower()
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        
    async def get_products(self, limit: int = 5) -> str:
        """
        Fetch products from the ecommerce store.
        
        Args:
            limit: Number of products to fetch (default: 5)
            
        Returns:
            Formatted string with product information
        """
        try:
            logger.info(f"📦 Fetching {limit} products from {self.platform}...")
            
            if self.platform == "woocommerce":
                url = f"{self.base_url}/products"
                params = {"per_page": limit}
                auth = BasicAuth(self.api_key, self.api_secret or "")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, auth=auth, params=params) as response:
                        if response.status == 200:
                            products = await response.json()
                            return self._format_woocommerce_products(products)
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ Failed to fetch products: {response.status} - {error_text}")
                            return f"Error fetching products: {response.status}"
            
            elif self.platform == "shopify":
                # Shopify implementation
                url = f"{self.base_url}/admin/api/2024-01/products.json"
                headers = {
                    "X-Shopify-Access-Token": self.access_token,
                    "Content-Type": "application/json"
                }
                params = {"limit": limit}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            products = data.get("products", [])
                            return self._format_shopify_products(products)
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ Failed to fetch products: {response.status} - {error_text}")
                            return f"Error fetching products: {response.status}"
            
            else:
                return f"Platform '{self.platform}' is not supported yet."
                
        except Exception as e:
            logger.error(f"Error in get_products: {e}")
            return f"Error fetching products: {str(e)}"
    
    async def get_orders(self, limit: int = 5) -> str:
        """
        Fetch recent orders from the ecommerce store.
        
        Args:
            limit: Number of orders to fetch (default: 5)
            
        Returns:
            Formatted string with order information
        """
        try:
            logger.info(f"🧾 Fetching {limit} orders from {self.platform}...")
            
            if self.platform == "woocommerce":
                url = f"{self.base_url}/orders"
                params = {"per_page": limit}
                auth = BasicAuth(self.api_key, self.api_secret or "")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, auth=auth, params=params) as response:
                        if response.status == 200:
                            orders = await response.json()
                            return self._format_woocommerce_orders(orders)
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ Failed to fetch orders: {response.status} - {error_text}")
                            return f"Error fetching orders: {response.status}"
            
            elif self.platform == "shopify":
                # Shopify implementation
                url = f"{self.base_url}/admin/api/2024-01/orders.json"
                headers = {
                    "X-Shopify-Access-Token": self.access_token,
                    "Content-Type": "application/json"
                }
                params = {"limit": limit, "status": "any"}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            orders = data.get("orders", [])
                            return self._format_shopify_orders(orders)
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ Failed to fetch orders: {response.status} - {error_text}")
                            return f"Error fetching orders: {response.status}"
            
            else:
                return f"Platform '{self.platform}' is not supported yet."
                
        except Exception as e:
            logger.error(f"Error in get_orders: {e}")
            return f"Error fetching orders: {str(e)}"
    
    def _format_woocommerce_products(self, products: List[Dict]) -> str:
        """Format WooCommerce products into readable text."""
        if not products:
            return "No products found."
        
        result = f"Found {len(products)} products:\n"
        for p in products:
            name = p.get('name', 'Unknown')
            price = p.get('price', '0')
            stock_status = p.get('stock_status', 'unknown')
            description = p.get('description', 'Unknown')
            url = p.get('permalink', 'Unknown')
            result += f"\n- {name}\n"
            result += f"  Price: ${price}\n"
            result += f"  Stock: {stock_status}\n"
            result += f"  Description: {description}\n"
            result += f"  URL: {url}\n"
        
        return result
    
    def _format_woocommerce_orders(self, orders: List[Dict]) -> str:
        """Format WooCommerce orders into readable text."""
        if not orders:
            return "No orders found."
        
        result = f"Found {len(orders)} recent orders:\n"
        for o in orders:
            order_id = o.get('id', 'Unknown')
            status = o.get('status', 'unknown')
            total = o.get('total', '0')
            date = o.get('date_created', 'Unknown')
            result += f"\n- Order #{order_id}\n"
            result += f"  Status: {status}\n"
            result += f"  Total: ${total}\n"
            result += f"  Date: {date}\n"
        
        return result
    
    def _format_shopify_products(self, products: List[Dict]) -> str:
        """Format Shopify products into readable text."""
        if not products:
            return "No products found."
        
        result = f"Found {len(products)} products:\n"
        for p in products:
            title = p.get('title', 'Unknown')
            variants = p.get('variants', [])
            price = variants[0].get('price', '0') if variants else '0'
            result += f"\n- {title}\n"
            result += f"  Price: ${price}\n"
        
        return result
    
    def _format_shopify_orders(self, orders: List[Dict]) -> str:
        """Format Shopify orders into readable text."""
        if not orders:
            return "No orders found."
        
        result = f"Found {len(orders)} recent orders:\n"
        for o in orders:
            order_id = o.get('id', 'Unknown')
            name = o.get('name', 'Unknown')
            status = o.get('financial_status', 'unknown')
            total = o.get('total_price', '0')
            result += f"\n- Order {name}\n"
            result += f"  Status: {status}\n"
            result += f"  Total: ${total}\n"
        
        return result


# Global client instance (will be set by agent_service)
_ecommerce_client: Optional[EcommerceClient] = None


def set_ecommerce_client(client: Optional[EcommerceClient]):
    """Set the global ecommerce client instance."""
    global _ecommerce_client
    _ecommerce_client = client


def get_ecommerce_client() -> Optional[EcommerceClient]:
    """Get the global ecommerce client instance."""
    return _ecommerce_client