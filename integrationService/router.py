"""
Integration Router
Provides a centralized way to manage and access all integrations with proper tagging and categorization.
"""

from typing import Dict, Any, Optional, List, Type
from enum import Enum


class IntegrationCategory(Enum):
    """Categories for different types of integrations"""
    ECOMMERCE = "ecommerce"
    BOOKING = "booking"
    SHIPPING = "shipping"
    AUTOMATION = "automation"
    MICROSERVICE = "microservice"
    GENERAL = "general"


class IntegrationTags(Enum):
    """Common tags for integration capabilities"""
    PRODUCTS = "products"
    ORDERS = "orders"
    CUSTOMERS = "customers"
    INVENTORY = "inventory"
    BOOKING_LINKS = "booking_links"
    API = "api"
    SHEETS = "sheets"
    OAUTH = "oauth"
    REST_API = "rest_api"
    ANALYTICS = "analytics"


class IntegrationRegistry:
    """
    Registry to store metadata about all available integrations.
    Provides tagging, categorization, and quick lookup.
    """
    
    _registry: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        client_class: Type,
        category: IntegrationCategory,
        tags: List[IntegrationTags],
        description: str = ""
    ):
        """
        Register an integration with metadata.
        
        :param name: Unique identifier for the integration
        :param client_class: The client class
        :param category: Integration category
        :param tags: List of capability tags
        :param description: Optional description
        """
        cls._registry[name] = {
            'class': client_class,
            'category': category,
            'tags': tags,
            'description': description,
            'instance': None
        }
    
    @classmethod
    def get_integration_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific integration"""
        return cls._registry.get(name)
    
    @classmethod
    def list_by_category(cls, category: IntegrationCategory) -> List[str]:
        """List all integrations in a category"""
        return [
            name for name, info in cls._registry.items()
            if info['category'] == category
        ]
    
    @classmethod
    def list_by_tag(cls, tag: IntegrationTags) -> List[str]:
        """List all integrations with a specific tag"""
        return [
            name for name, info in cls._registry.items()
            if tag in info['tags']
        ]
    
    @classmethod
    def list_all(cls) -> Dict[str, Dict[str, Any]]:
        """Get all registered integrations"""
        return {
            name: {
                'category': info['category'].value,
                'tags': [tag.value for tag in info['tags']],
                'description': info['description'],
                'initialized': info['instance'] is not None
            }
            for name, info in cls._registry.items()
        }
    
    @classmethod
    def search(cls, query: str) -> List[str]:
        """Search integrations by name or description"""
        query_lower = query.lower()
        return [
            name for name, info in cls._registry.items()
            if query_lower in name.lower() or query_lower in info['description'].lower()
        ]


class IntegrationRouter:
    """
    Main router for accessing and managing integrations.
    Provides a clean interface to initialize and use integration clients.
    """
    
    def __init__(self):
        """Initialize the router"""
        self._clients: Dict[str, Any] = {}
    
    def register_client(self, name: str, client_instance: Any):
        """
        Register an initialized client instance.
        
        :param name: Integration name (must be registered in IntegrationRegistry)
        :param client_instance: Initialized client object
        """
        if name not in IntegrationRegistry._registry:
            raise ValueError(f"Integration '{name}' not found in registry. Please register it first.")
        
        # Verify the instance type
        expected_class = IntegrationRegistry._registry[name]['class']
        if not isinstance(client_instance, expected_class):
            raise TypeError(
                f"Client instance for '{name}' must be of type {expected_class.__name__}, "
                f"got {type(client_instance).__name__}"
            )
        
        self._clients[name] = client_instance
        IntegrationRegistry._registry[name]['instance'] = client_instance
    
    def get_client(self, name: str) -> Any:
        """
        Get an initialized client by name.
        
        :param name: Integration name
        :return: Client instance
        :raises KeyError: If client not found or not initialized
        """
        if name not in self._clients:
            raise KeyError(
                f"Client '{name}' not initialized. "
                f"Use register_client() to add it first."
            )
        return self._clients[name]
    
    def has_client(self, name: str) -> bool:
        """Check if a client is registered and initialized"""
        return name in self._clients
    
    def list_initialized_clients(self) -> List[str]:
        """Get list of all initialized client names"""
        return list(self._clients.keys())
    
    def get_clients_by_category(self, category: IntegrationCategory) -> Dict[str, Any]:
        """
        Get all initialized clients in a specific category.
        
        :param category: Integration category
        :return: Dictionary of {name: client_instance}
        """
        category_names = IntegrationRegistry.list_by_category(category)
        return {
            name: self._clients[name]
            for name in category_names
            if name in self._clients
        }
    
    def get_clients_by_tag(self, tag: IntegrationTags) -> Dict[str, Any]:
        """
        Get all initialized clients with a specific tag.
        
        :param tag: Integration tag
        :return: Dictionary of {name: client_instance}
        """
        tag_names = IntegrationRegistry.list_by_tag(tag)
        return {
            name: self._clients[name]
            for name in tag_names
            if name in self._clients
        }
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test connectivity for all initialized clients that support it.
        
        :return: Dictionary of {name: connection_status}
        """
        results = {}
        for name, client in self._clients.items():
            if hasattr(client, 'test_connection'):
                try:
                    results[name] = client.test_connection()
                except Exception as e:
                    results[name] = False
            else:
                results[name] = None  # Method not available
        return results
    
    def remove_client(self, name: str):
        """Remove a client from the router"""
        if name in self._clients:
            del self._clients[name]
            if name in IntegrationRegistry._registry:
                IntegrationRegistry._registry[name]['instance'] = None
    
    def clear_all(self):
        """Remove all clients from the router"""
        self._clients.clear()
        for info in IntegrationRegistry._registry.values():
            info['instance'] = None


# ==============================================
# Auto-register all available integrations
# ==============================================

def _auto_register_integrations():
    """Automatically register all integration clients"""
    
    try:
        from .shopify import ShopifyClient
        IntegrationRegistry.register(
            name="shopify",
            client_class=ShopifyClient,
            category=IntegrationCategory.ECOMMERCE,
            tags=[
                IntegrationTags.PRODUCTS,
                IntegrationTags.ORDERS,
                IntegrationTags.REST_API,
                IntegrationTags.API
            ],
            description="Shopify e-commerce platform integration"
        )
    except ImportError:
        pass
    
    try:
        from .WooCommerce import WooCommerceClient
        IntegrationRegistry.register(
            name="woocommerce",
            client_class=WooCommerceClient,
            category=IntegrationCategory.ECOMMERCE,
            tags=[
                IntegrationTags.PRODUCTS,
                IntegrationTags.ORDERS,
                IntegrationTags.REST_API,
                IntegrationTags.API
            ],
            description="WooCommerce WordPress e-commerce plugin integration"
        )
    except ImportError:
        pass
    
    try:
        from .magento2_client import Magento2Client
        IntegrationRegistry.register(
            name="magento2",
            client_class=Magento2Client,
            category=IntegrationCategory.ECOMMERCE,
            tags=[
                IntegrationTags.PRODUCTS,
                IntegrationTags.ORDERS,
                IntegrationTags.REST_API,
                IntegrationTags.OAUTH,
                IntegrationTags.API
            ],
            description="Magento 2 e-commerce platform integration"
        )
    except ImportError:
        pass
    
    try:
        from .Prestashop import PrestashopClient
        IntegrationRegistry.register(
            name="prestashop",
            client_class=PrestashopClient,
            category=IntegrationCategory.ECOMMERCE,
            tags=[
                IntegrationTags.PRODUCTS,
                IntegrationTags.ORDERS,
                IntegrationTags.REST_API,
                IntegrationTags.API
            ],
            description="PrestaShop e-commerce platform integration"
        )
    except ImportError:
        pass
    
    try:
        from .Qapla import QaplaClient
        IntegrationRegistry.register(
            name="qapla",
            client_class=QaplaClient,
            category=IntegrationCategory.SHIPPING,
            tags=[
                IntegrationTags.ORDERS,
                IntegrationTags.PRODUCTS,
                IntegrationTags.REST_API,
                IntegrationTags.API
            ],
            description="Qapla shipping and logistics integration"
        )
    except ImportError:
        pass
    
    try:
        from .VerticalBooking import VerticalBookingClient
        IntegrationRegistry.register(
            name="vertical_booking",
            client_class=VerticalBookingClient,
            category=IntegrationCategory.BOOKING,
            tags=[
                IntegrationTags.BOOKING_LINKS,
                IntegrationTags.API
            ],
            description="Vertical Booking hotel reservation system"
        )
    except ImportError:
        pass
    
    try:
        from .BookingExpert import BookingExpertClient
        IntegrationRegistry.register(
            name="booking_expert",
            client_class=BookingExpertClient,
            category=IntegrationCategory.BOOKING,
            tags=[
                IntegrationTags.BOOKING_LINKS,
                IntegrationTags.API
            ],
            description="Booking Expert reservation system"
        )
    except ImportError:
        pass
    
    try:
        from .mcp import MCPClient
        IntegrationRegistry.register(
            name="mcp",
            client_class=MCPClient,
            category=IntegrationCategory.MICROSERVICE,
            tags=[
                IntegrationTags.API,
                IntegrationTags.REST_API
            ],
            description="Generic microservice client for custom API integrations"
        )
    except ImportError:
        pass
    
    try:
        from .AutomaticLabelling import KeplerGoogleSheet
        IntegrationRegistry.register(
            name="google_sheets",
            client_class=KeplerGoogleSheet,
            category=IntegrationCategory.AUTOMATION,
            tags=[
                IntegrationTags.SHEETS,
                IntegrationTags.ANALYTICS,
                IntegrationTags.API
            ],
            description="Google Sheets integration for data automation"
        )
    except ImportError:
        pass


# Auto-register on module load
_auto_register_integrations()

