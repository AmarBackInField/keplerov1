"""
Integration Service Package
Provides a unified router for all third-party integrations.
"""

from .router import IntegrationRouter, IntegrationRegistry, IntegrationCategory, IntegrationTags
from .shopify import ShopifyClient
from .WooCommerce import WooCommerceClient
from .magento2_client import Magento2Client
from .Prestashop import PrestashopClient
from .Qapla import QaplaClient
from .VerticalBooking import VerticalBookingClient
from .BookingExpert import BookingExpertClient
from .mcp import MCPClient
from .AutomaticLabelling import KeplerGoogleSheet
from .config_helper import IntegrationConfigManager, IntegrationValidator

__all__ = [
    'IntegrationRouter',
    'IntegrationRegistry',
    'IntegrationCategory',
    'IntegrationTags',
    'ShopifyClient',
    'WooCommerceClient',
    'Magento2Client',
    'PrestashopClient',
    'QaplaClient',
    'VerticalBookingClient',
    'BookingExpertClient',
    'MCPClient',
    'KeplerGoogleSheet',
    'IntegrationConfigManager',
    'IntegrationValidator',
]

__version__ = '1.0.0'

