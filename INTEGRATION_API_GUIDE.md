# Integration Service API Guide

## 📋 Postman Collection

The `Integration_Service_API.postman_collection.json` file contains all endpoints for managing integrations.

## 🚀 Quick Start

### 1. Import into Postman
1. Open Postman
2. Click **Import** button
3. Select `Integration_Service_API.postman_collection.json`
4. Collection will appear in your workspace

### 2. Set Base URL
The collection uses a variable `{{base_url}}` which defaults to `http://localhost:8000`

To change it:
- Click on the collection name
- Go to **Variables** tab
- Update `base_url` value

---

## 📚 Collection Structure

### 1. Health Check
- **API Health Check** - Check service status
- **Root Endpoint** - Get API information

### 2. Integration Setup (9 Endpoints)
Initialize integrations before use:
- Shopify
- WooCommerce
- Magento2
- PrestaShop
- Qapla
- Vertical Booking
- Booking Expert
- MCP Client
- Google Sheets

### 3. E-commerce Operations (4 Endpoints)
Perform operations on e-commerce platforms:
- List Products
- Get Single Product
- List Orders
- Get Single Order

**Supported Platforms**: shopify, woocommerce, magento2, prestashop, qapla

### 4. Booking Operations (2 Endpoints)
Generate booking links:
- Vertical Booking Link Generator
- Booking Expert Link Generator

### 5. MCP Microservice (4 Endpoints)
Make HTTP requests to custom APIs:
- GET Request
- POST Request
- PUT Request
- DELETE Request

### 6. Registry & Discovery (8 Endpoints)
Discover available integrations:
- List All Integrations
- Filter by Category (ecommerce, booking, shipping, automation, microservice)
- Filter by Tag (products, orders, booking_links, sheets, api, etc.)
- Search Integrations

### 7. Status & Management (4 Endpoints)
Monitor and manage integrations:
- List Initialized Clients
- Test All Connections
- Remove Single Integration
- Remove All Integrations

---

## 🔑 Configuration Examples

### E-commerce Platforms

#### Shopify
```json
{
  "shop_url": "mystore.myshopify.com",
  "admin_api_key": "shpat_xxxxxxxxxxxxx",
  "api_version": "2024-10"
}
```

#### WooCommerce
```json
{
  "store_url": "https://mystore.com",
  "consumer_key": "ck_xxxxxxxxxxxxxxxx",
  "consumer_secret": "cs_xxxxxxxxxxxxxxxx",
  "api_version": "wc/v3"
}
```

#### Magento2
```json
{
  "store_url": "https://magento-store.com",
  "consumer_key": "xxxxx",
  "consumer_secret": "xxxxx",
  "access_token": "xxxxx",
  "access_token_secret": "xxxxx",
  "api_version": "V1"
}
```

#### PrestaShop
```json
{
  "store_url": "https://prestashop-store.com",
  "api_key": "XXXXXXXXXXXXXXXXXXXXXXXX",
  "api_version": "api"
}
```

### Booking Systems

#### Vertical Booking
```json
{
  "hotel_id": "hotel123",
  "style_id": "style456",
  "dc": "DC001",
  "base_url": "https://booking.verticalbooking.com"
}
```

#### Booking Expert
```json
{
  "engine_url": "https://engine.bookingexpert.com",
  "layout_id": "layout123",
  "adult_type_id": "1",
  "teen_type_id": "2",
  "child_type_id": "3"
}
```

### Shipping & Logistics

#### Qapla
```json
{
  "api_key": "your_qapla_api_key",
  "base_url": "https://api.qapla.it/v1"
}
```

### Automation

#### Google Sheets
```json
{
  "creds_json_path": "/path/to/service-account.json",
  "sheet_name": "My Data Sheet",
  "worksheet_name": "Sheet1"
}
```

### Microservice

#### MCP Client
```json
{
  "name": "my-microservice",
  "url": "https://api.myservice.com/endpoint",
  "headers": {
    "Authorization": "Bearer your_token",
    "X-Custom-Header": "value"
  }
}
```

---

## 🎯 Common Workflows

### Workflow 1: Setup and Use E-commerce Integration

1. **Setup Shopify**
   ```
   POST /integration/setup/shopify
   ```

2. **List Products**
   ```
   POST /integration/ecommerce/shopify/execute
   Body: {"operation": "list_products", "limit": 50}
   ```

3. **Get Product Details**
   ```
   POST /integration/ecommerce/shopify/execute
   Body: {"operation": "get_product", "product_id": "123"}
   ```

### Workflow 2: Generate Booking Links

1. **Setup Vertical Booking**
   ```
   POST /integration/setup/vertical-booking
   ```

2. **Generate Booking Link**
   ```
   POST /integration/booking/vertical_booking/generate-link
   Body: {
     "check_in": "2025-12-01",
     "check_out": "2025-12-05",
     "adults": 2,
     "children": 1
   }
   ```

### Workflow 3: Monitor Integration Health

1. **Check Initialized Integrations**
   ```
   GET /integration/status/initialized
   ```

2. **Test All Connections**
   ```
   GET /integration/status/test-connections
   ```

---

## 🏷️ Categories and Tags Reference

### Categories
- **ecommerce** - E-commerce platforms (Shopify, WooCommerce, Magento2, PrestaShop)
- **booking** - Hotel/reservation systems (Vertical Booking, Booking Expert)
- **shipping** - Logistics platforms (Qapla)
- **automation** - Automation tools (Google Sheets)
- **microservice** - Generic API clients (MCP)

### Tags
- **products** - Product management operations
- **orders** - Order management operations
- **customers** - Customer management
- **inventory** - Inventory tracking
- **booking_links** - Booking link generation
- **sheets** - Spreadsheet operations
- **analytics** - Analytics and reporting
- **api** - Generic API access
- **rest_api** - RESTful API
- **oauth** - OAuth authentication

---

## 🔍 Discovery Endpoints

### Find All E-commerce Integrations
```
GET /integration/registry/by-category/ecommerce
```

### Find All Integrations with Product Support
```
GET /integration/registry/by-tag/products
```

### Search for Specific Integration
```
GET /integration/registry/search?query=shopify
```

---

## 📊 Response Examples

### Successful Setup Response
```json
{
  "status": "success",
  "message": "Shopify integration initialized successfully",
  "integration": "shopify",
  "category": "ecommerce",
  "tags": ["products", "orders", "rest_api"]
}
```

### E-commerce Operation Response
```json
{
  "status": "success",
  "integration": "shopify",
  "operation": "list_products",
  "data": {
    "products": [...]
  }
}
```

### Booking Link Response
```json
{
  "status": "success",
  "integration": "vertical_booking",
  "booking_link": "https://booking.verticalbooking.com/book?hotel=hotel123&checkin=2025-12-01&checkout=2025-12-05&adults=2&children=1"
}
```

### Connection Test Response
```json
{
  "status": "success",
  "connection_tests": {
    "shopify": true,
    "woocommerce": true,
    "vertical_booking": true,
    "mcp": null
  }
}
```

---

## ⚠️ Error Handling

### Common Errors

#### Integration Not Initialized (404)
```json
{
  "detail": "Integration 'shopify' not initialized. Please setup first."
}
```

**Solution**: Call the setup endpoint first

#### Missing Required Field (400)
```json
{
  "detail": "product_id is required"
}
```

**Solution**: Include all required fields in request body

#### Connection Failed (500)
```json
{
  "detail": "Error details..."
}
```

**Solution**: Check credentials and network connectivity

---

## 🛠️ Environment Variables (Optional)

You can load configurations from environment variables using the config helper:

```bash
# Shopify
SHOPIFY_SHOP_URL=mystore.myshopify.com
SHOPIFY_ADMIN_API_KEY=shpat_xxxxx
SHOPIFY_API_VERSION=2024-10

# WooCommerce
WOOCOMMERCE_STORE_URL=https://mystore.com
WOOCOMMERCE_CONSUMER_KEY=ck_xxxxx
WOOCOMMERCE_CONSUMER_SECRET=cs_xxxxx

# Magento2
MAGENTO2_STORE_URL=https://magento-store.com
MAGENTO2_CONSUMER_KEY=xxxxx
MAGENTO2_CONSUMER_SECRET=xxxxx
MAGENTO2_ACCESS_TOKEN=xxxxx
MAGENTO2_ACCESS_TOKEN_SECRET=xxxxx
```

---

## 📝 Notes

1. **Setup First**: Always setup an integration before using its operations
2. **Test Connections**: Use the test endpoint to verify connectivity
3. **Error Handling**: Check response status codes and error messages
4. **Rate Limits**: Be aware of third-party API rate limits
5. **Security**: Never commit API keys to version control

---

## 🔗 Useful Links

- **API Documentation**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

---

## 💡 Tips

1. Use Postman **Environments** to manage multiple configurations (dev, staging, prod)
2. Set up **Tests** in Postman to automatically validate responses
3. Use **Collections Runner** to test multiple endpoints in sequence
4. Save common requests to **Examples** for quick reference
5. Use **Variables** for dynamic values like product IDs and order IDs

---

## 🆘 Support

For issues or questions:
1. Check the `/docs` endpoint for interactive API documentation
2. Review error messages in responses
3. Verify integration credentials
4. Test connectivity using `/integration/status/test-connections`

---

**Last Updated**: November 2025  
**API Version**: 1.0.0

