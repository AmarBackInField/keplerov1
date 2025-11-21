"""
Integration Router
FastAPI endpoints for managing third-party integrations
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from integrationService import IntegrationRouter, IntegrationRegistry, IntegrationCategory, IntegrationTags
from integrationService import (
    ShopifyClient,
    WooCommerceClient,
    Magento2Client,
    PrestashopClient,
    QaplaClient,
    VerticalBookingClient,
    BookingExpertClient,
    MCPClient,
    KeplerGoogleSheet
)

# Initialize router
router = APIRouter(
    prefix="/integration",
    tags=["Integration"]
)

# Global integration router instance
integration_router = IntegrationRouter()


# ==================== Request Models ====================

class ShopifyConfigModel(BaseModel):
    """Configuration for Shopify integration"""
    shop_url: str = Field(..., description="Shopify store URL (e.g. mystore.myshopify.com)")
    admin_api_key: str = Field(..., description="Admin API Access Token")
    api_version: str = Field(default="2024-10", description="Shopify API version")


class WooCommerceConfigModel(BaseModel):
    """Configuration for WooCommerce integration"""
    store_url: str = Field(..., description="WooCommerce store URL")
    consumer_key: str = Field(..., description="WooCommerce Consumer Key")
    consumer_secret: str = Field(..., description="WooCommerce Consumer Secret")
    api_version: str = Field(default="wc/v3", description="API version")


class Magento2ConfigModel(BaseModel):
    """Configuration for Magento2 integration"""
    store_url: str = Field(..., description="Magento store URL")
    consumer_key: str = Field(..., description="Magento Consumer Key")
    consumer_secret: str = Field(..., description="Magento Consumer Secret")
    access_token: str = Field(..., description="OAuth Access Token")
    access_token_secret: str = Field(..., description="OAuth Access Token Secret")
    api_version: str = Field(default="V1", description="API version")


class PrestashopConfigModel(BaseModel):
    """Configuration for Prestashop integration"""
    store_url: str = Field(..., description="Prestashop store URL")
    api_key: str = Field(..., description="Prestashop API key")
    api_version: str = Field(default="api", description="API version")


class QaplaConfigModel(BaseModel):
    """Configuration for Qapla integration"""
    api_key: str = Field(..., description="Qapla API Key")
    base_url: str = Field(default="https://api.qapla.it/v1", description="Qapla API base URL")


class VerticalBookingConfigModel(BaseModel):
    """Configuration for Vertical Booking integration"""
    hotel_id: str = Field(..., description="Hotel ID")
    style_id: str = Field(..., description="Style ID")
    dc: str = Field(..., description="Distribution Channel code")
    base_url: str = Field(default="https://booking.verticalbooking.com", description="Base URL")


class BookingExpertConfigModel(BaseModel):
    """Configuration for Booking Expert integration"""
    engine_url: str = Field(..., description="Booking Expert engine URL")
    layout_id: str = Field(..., description="Layout ID")
    adult_type_id: str = Field(..., description="Adult guest type ID")
    teen_type_id: str = Field(..., description="Teen guest type ID")
    child_type_id: str = Field(..., description="Child guest type ID")


class MCPConfigModel(BaseModel):
    """Configuration for MCP client"""
    name: str = Field(..., description="MCP client name")
    url: str = Field(..., description="MCP endpoint URL")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Optional headers")


class GoogleSheetsConfigModel(BaseModel):
    """Configuration for Google Sheets integration"""
    creds_json_path: str = Field(..., description="Path to Google service account JSON")
    sheet_name: str = Field(..., description="Google Sheet name")
    worksheet_name: str = Field(default="Sheet1", description="Worksheet name")


class BookingLinkRequestModel(BaseModel):
    """Request model for generating booking links"""
    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(default=1, description="Number of adults")
    children: int = Field(default=0, description="Number of children")
    teens: Optional[int] = Field(default=0, description="Number of teens (for BookingExpert)")
    hotel_id: Optional[str] = Field(default=None, description="Hotel ID (for BookingExpert)")
    extra_params: Optional[Dict[str, Any]] = Field(default=None, description="Extra parameters")


class EcommerceRequestModel(BaseModel):
    """Request model for e-commerce operations"""
    operation: str = Field(..., description="Operation type: list_products, get_product, list_orders, get_order")
    product_id: Optional[Any] = Field(default=None, description="Product ID (for get_product)")
    order_id: Optional[Any] = Field(default=None, description="Order ID (for get_order)")
    limit: Optional[int] = Field(default=50, description="Limit for list operations")
    page: Optional[int] = Field(default=1, description="Page number")


class MCPRequestModel(BaseModel):
    """Request model for MCP operations"""
    method: str = Field(default="GET", description="HTTP method")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Request data")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")


# ==================== Integration Setup Endpoints ====================

@router.post("/setup/shopify", tags=["Setup"])
async def setup_shopify(config: ShopifyConfigModel):
    """
    Initialize and register Shopify integration
    
    **Tags**: ecommerce, products, orders, rest_api
    """
    try:
        client = ShopifyClient(
            shop_url=config.shop_url,
            admin_api_key=config.admin_api_key,
            api_version=config.api_version
        )
        integration_router.register_client("shopify", client)
        
        return {
            "status": "success",
            "message": "Shopify integration initialized successfully",
            "integration": "shopify",
            "category": "ecommerce",
            "tags": ["products", "orders", "rest_api"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/woocommerce", tags=["Setup"])
async def setup_woocommerce(config: WooCommerceConfigModel):
    """
    Initialize and register WooCommerce integration
    
    **Tags**: ecommerce, products, orders, rest_api
    """
    try:
        client = WooCommerceClient(
            store_url=config.store_url,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            api_version=config.api_version
        )
        integration_router.register_client("woocommerce", client)
        
        return {
            "status": "success",
            "message": "WooCommerce integration initialized successfully",
            "integration": "woocommerce",
            "category": "ecommerce",
            "tags": ["products", "orders", "rest_api"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/magento2", tags=["Setup"])
async def setup_magento2(config: Magento2ConfigModel):
    """
    Initialize and register Magento2 integration
    
    **Tags**: ecommerce, products, orders, rest_api, oauth
    """
    try:
        client = Magento2Client(
            store_url=config.store_url,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret,
            access_token=config.access_token,
            access_token_secret=config.access_token_secret,
            api_version=config.api_version
        )
        integration_router.register_client("magento2", client)
        
        return {
            "status": "success",
            "message": "Magento2 integration initialized successfully",
            "integration": "magento2",
            "category": "ecommerce",
            "tags": ["products", "orders", "rest_api", "oauth"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/prestashop", tags=["Setup"])
async def setup_prestashop(config: PrestashopConfigModel):
    """
    Initialize and register Prestashop integration
    
    **Tags**: ecommerce, products, orders, rest_api
    """
    try:
        client = PrestashopClient(
            store_url=config.store_url,
            api_key=config.api_key,
            api_version=config.api_version
        )
        integration_router.register_client("prestashop", client)
        
        return {
            "status": "success",
            "message": "Prestashop integration initialized successfully",
            "integration": "prestashop",
            "category": "ecommerce",
            "tags": ["products", "orders", "rest_api"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/qapla", tags=["Setup"])
async def setup_qapla(config: QaplaConfigModel):
    """
    Initialize and register Qapla integration
    
    **Tags**: shipping, orders, products, rest_api
    """
    try:
        client = QaplaClient(
            api_key=config.api_key,
            base_url=config.base_url
        )
        integration_router.register_client("qapla", client)
        
        return {
            "status": "success",
            "message": "Qapla integration initialized successfully",
            "integration": "qapla",
            "category": "shipping",
            "tags": ["orders", "products", "rest_api"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/vertical-booking", tags=["Setup"])
async def setup_vertical_booking(config: VerticalBookingConfigModel):
    """
    Initialize and register Vertical Booking integration
    
    **Tags**: booking, booking_links
    """
    try:
        client = VerticalBookingClient(
            hotel_id=config.hotel_id,
            style_id=config.style_id,
            dc=config.dc,
            base_url=config.base_url
        )
        integration_router.register_client("vertical_booking", client)
        
        return {
            "status": "success",
            "message": "Vertical Booking integration initialized successfully",
            "integration": "vertical_booking",
            "category": "booking",
            "tags": ["booking_links"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/booking-expert", tags=["Setup"])
async def setup_booking_expert(config: BookingExpertConfigModel):
    """
    Initialize and register Booking Expert integration
    
    **Tags**: booking, booking_links
    """
    try:
        client = BookingExpertClient(
            engine_url=config.engine_url,
            layout_id=config.layout_id,
            adult_type_id=config.adult_type_id,
            teen_type_id=config.teen_type_id,
            child_type_id=config.child_type_id
        )
        integration_router.register_client("booking_expert", client)
        
        return {
            "status": "success",
            "message": "Booking Expert integration initialized successfully",
            "integration": "booking_expert",
            "category": "booking",
            "tags": ["booking_links"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/mcp", tags=["Setup"])
async def setup_mcp(config: MCPConfigModel):
    """
    Initialize and register MCP client
    
    **Tags**: microservice, api, rest_api
    """
    try:
        client = MCPClient(
            name=config.name,
            url=config.url,
            headers=config.headers
        )
        integration_router.register_client("mcp", client)
        
        return {
            "status": "success",
            "message": "MCP client initialized successfully",
            "integration": "mcp",
            "category": "microservice",
            "tags": ["api", "rest_api"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup/google-sheets", tags=["Setup"])
async def setup_google_sheets(config: GoogleSheetsConfigModel):
    """
    Initialize and register Google Sheets integration
    
    **Tags**: automation, sheets, analytics
    """
    try:
        client = KeplerGoogleSheet(
            creds_json_path=config.creds_json_path,
            sheet_name=config.sheet_name,
            worksheet_name=config.worksheet_name
        )
        integration_router.register_client("google_sheets", client)
        
        return {
            "status": "success",
            "message": "Google Sheets integration initialized successfully",
            "integration": "google_sheets",
            "category": "automation",
            "tags": ["sheets", "analytics"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== E-commerce Operations ====================

@router.post("/ecommerce/{integration_name}/execute", tags=["E-commerce"])
async def execute_ecommerce_operation(
    integration_name: str,
    request: EcommerceRequestModel
):
    """
    Execute e-commerce operations (products, orders) on any e-commerce integration
    
    **Supported integrations**: shopify, woocommerce, magento2, prestashop, qapla
    
    **Operations**:
    - list_products: Get list of products
    - get_product: Get single product details
    - list_orders: Get list of orders
    - get_order: Get single order details
    """
    try:
        if not integration_router.has_client(integration_name):
            raise HTTPException(
                status_code=404,
                detail=f"Integration '{integration_name}' not initialized. Please setup first."
            )
        
        client = integration_router.get_client(integration_name)
        
        if request.operation == "list_products":
            if hasattr(client, 'list_products'):
                result = client.list_products(limit=request.limit or 50)
            elif hasattr(client, 'get_all_products'):
                result = client.get_all_products(limit=request.limit or 50)
            else:
                raise HTTPException(status_code=400, detail="Operation not supported")
                
        elif request.operation == "get_product":
            if not request.product_id:
                raise HTTPException(status_code=400, detail="product_id is required")
            result = client.get_product(request.product_id)
            
        elif request.operation == "list_orders":
            if hasattr(client, 'list_orders'):
                result = client.list_orders(limit=request.limit or 50)
            elif hasattr(client, 'get_all_orders'):
                result = client.get_all_orders(limit=request.limit or 50)
            else:
                raise HTTPException(status_code=400, detail="Operation not supported")
                
        elif request.operation == "get_order":
            if not request.order_id:
                raise HTTPException(status_code=400, detail="order_id is required")
            result = client.get_order(request.order_id)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown operation: {request.operation}"
            )
        
        return {
            "status": "success",
            "integration": integration_name,
            "operation": request.operation,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Booking Operations ====================

@router.post("/booking/{integration_name}/generate-link", tags=["Booking"])
async def generate_booking_link(
    integration_name: str,
    request: BookingLinkRequestModel
):
    """
    Generate booking links for hotel reservations
    
    **Supported integrations**: vertical_booking, booking_expert
    """
    try:
        if not integration_router.has_client(integration_name):
            raise HTTPException(
                status_code=404,
                detail=f"Integration '{integration_name}' not initialized. Please setup first."
            )
        
        client = integration_router.get_client(integration_name)
        
        if integration_name == "vertical_booking":
            link = client.generate_booking_link(
                check_in=request.check_in,
                check_out=request.check_out,
                adults=request.adults,
                children=request.children,
                extra_params=request.extra_params
            )
        elif integration_name == "booking_expert":
            if not request.hotel_id:
                raise HTTPException(status_code=400, detail="hotel_id is required for BookingExpert")
            link = client.generate_booking_link(
                hotel_id=request.hotel_id,
                check_in=request.check_in,
                check_out=request.check_out,
                adults=request.adults,
                teens=request.teens or 0,
                children=request.children,
                extra_params=request.extra_params
            )
        else:
            raise HTTPException(status_code=400, detail="Integration does not support booking links")
        
        return {
            "status": "success",
            "integration": integration_name,
            "booking_link": link
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MCP Operations ====================

@router.post("/mcp/request", tags=["Microservice"])
async def mcp_make_request(request: MCPRequestModel):
    """
    Make HTTP request using MCP client
    
    **Methods**: GET, POST, PUT, DELETE
    """
    try:
        if not integration_router.has_client("mcp"):
            raise HTTPException(
                status_code=404,
                detail="MCP client not initialized. Please setup first."
            )
        
        client = integration_router.get_client("mcp")
        result = client.make_request(
            method=request.method,
            data=request.data,
            params=request.params
        )
        
        return {
            "status": "success",
            "method": request.method,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Registry & Discovery Endpoints ====================

@router.get("/registry/list-all", tags=["Registry"])
async def list_all_integrations():
    """
    List all available integrations with their metadata
    """
    return {
        "status": "success",
        "integrations": IntegrationRegistry.list_all()
    }


@router.get("/registry/by-category/{category}", tags=["Registry"])
async def list_by_category(category: str):
    """
    List integrations by category
    
    **Categories**: ecommerce, booking, shipping, automation, microservice, general
    """
    try:
        cat_enum = IntegrationCategory(category)
        integrations = IntegrationRegistry.list_by_category(cat_enum)
        
        return {
            "status": "success",
            "category": category,
            "integrations": integrations
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Valid values: {[c.value for c in IntegrationCategory]}"
        )


@router.get("/registry/by-tag/{tag}", tags=["Registry"])
async def list_by_tag(tag: str):
    """
    List integrations by capability tag
    
    **Tags**: products, orders, customers, inventory, booking_links, api, sheets, oauth, rest_api, analytics
    """
    try:
        tag_enum = IntegrationTags(tag)
        integrations = IntegrationRegistry.list_by_tag(tag_enum)
        
        return {
            "status": "success",
            "tag": tag,
            "integrations": integrations
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tag. Valid values: {[t.value for t in IntegrationTags]}"
        )


@router.get("/registry/search", tags=["Registry"])
async def search_integrations(query: str):
    """
    Search integrations by name or description
    """
    results = IntegrationRegistry.search(query)
    
    return {
        "status": "success",
        "query": query,
        "results": results
    }


@router.get("/status/initialized", tags=["Status"])
async def list_initialized_clients():
    """
    Get list of all initialized integrations
    """
    return {
        "status": "success",
        "initialized_clients": integration_router.list_initialized_clients()
    }


@router.get("/status/test-connections", tags=["Status"])
async def test_all_connections():
    """
    Test connectivity for all initialized integrations
    """
    results = integration_router.test_connections()
    
    return {
        "status": "success",
        "connection_tests": results
    }


@router.delete("/remove/{integration_name}", tags=["Management"])
async def remove_integration(integration_name: str):
    """
    Remove an initialized integration
    """
    try:
        if not integration_router.has_client(integration_name):
            raise HTTPException(
                status_code=404,
                detail=f"Integration '{integration_name}' not found"
            )
        
        integration_router.remove_client(integration_name)
        
        return {
            "status": "success",
            "message": f"Integration '{integration_name}' removed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/remove-all", tags=["Management"])
async def remove_all_integrations():
    """
    Remove all initialized integrations
    """
    try:
        integration_router.clear_all()
        
        return {
            "status": "success",
            "message": "All integrations removed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

