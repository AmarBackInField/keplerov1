"""
Configuration Helper
Utilities for managing integration configurations securely
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import json


class IntegrationConfigManager:
    """
    Helper class to manage integration configurations.
    Supports loading from environment variables or config files.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        :param config_file: Optional path to JSON config file
        """
        self.config_file = config_file
        self._configs: Dict[str, Dict[str, Any]] = {}
        
        if config_file and Path(config_file).exists():
            self.load_from_file(config_file)
    
    def load_from_file(self, file_path: str):
        """Load configurations from JSON file"""
        with open(file_path, 'r') as f:
            self._configs = json.load(f)
    
    def save_to_file(self, file_path: str):
        """Save configurations to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(self._configs, f, indent=2)
    
    def set_config(self, integration_name: str, config: Dict[str, Any]):
        """
        Store configuration for an integration.
        
        :param integration_name: Name of the integration
        :param config: Configuration dictionary
        """
        self._configs[integration_name] = config
    
    def get_config(self, integration_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for an integration.
        
        :param integration_name: Name of the integration
        :return: Configuration dictionary or None
        """
        return self._configs.get(integration_name)
    
    def remove_config(self, integration_name: str):
        """Remove configuration for an integration"""
        if integration_name in self._configs:
            del self._configs[integration_name]
    
    def list_configured(self) -> list:
        """List all configured integrations"""
        return list(self._configs.keys())
    
    # ==================== Environment Variable Loaders ====================
    
    @staticmethod
    def get_shopify_config_from_env() -> Dict[str, str]:
        """Load Shopify configuration from environment variables"""
        return {
            "shop_url": os.getenv("SHOPIFY_SHOP_URL", ""),
            "admin_api_key": os.getenv("SHOPIFY_ADMIN_API_KEY", ""),
            "api_version": os.getenv("SHOPIFY_API_VERSION", "2024-10")
        }
    
    @staticmethod
    def get_woocommerce_config_from_env() -> Dict[str, str]:
        """Load WooCommerce configuration from environment variables"""
        return {
            "store_url": os.getenv("WOOCOMMERCE_STORE_URL", ""),
            "consumer_key": os.getenv("WOOCOMMERCE_CONSUMER_KEY", ""),
            "consumer_secret": os.getenv("WOOCOMMERCE_CONSUMER_SECRET", ""),
            "api_version": os.getenv("WOOCOMMERCE_API_VERSION", "wc/v3")
        }
    
    @staticmethod
    def get_magento2_config_from_env() -> Dict[str, str]:
        """Load Magento2 configuration from environment variables"""
        return {
            "store_url": os.getenv("MAGENTO2_STORE_URL", ""),
            "consumer_key": os.getenv("MAGENTO2_CONSUMER_KEY", ""),
            "consumer_secret": os.getenv("MAGENTO2_CONSUMER_SECRET", ""),
            "access_token": os.getenv("MAGENTO2_ACCESS_TOKEN", ""),
            "access_token_secret": os.getenv("MAGENTO2_ACCESS_TOKEN_SECRET", ""),
            "api_version": os.getenv("MAGENTO2_API_VERSION", "V1")
        }
    
    @staticmethod
    def get_prestashop_config_from_env() -> Dict[str, str]:
        """Load Prestashop configuration from environment variables"""
        return {
            "store_url": os.getenv("PRESTASHOP_STORE_URL", ""),
            "api_key": os.getenv("PRESTASHOP_API_KEY", ""),
            "api_version": os.getenv("PRESTASHOP_API_VERSION", "api")
        }
    
    @staticmethod
    def get_qapla_config_from_env() -> Dict[str, str]:
        """Load Qapla configuration from environment variables"""
        return {
            "api_key": os.getenv("QAPLA_API_KEY", ""),
            "base_url": os.getenv("QAPLA_BASE_URL", "https://api.qapla.it/v1")
        }
    
    @staticmethod
    def get_vertical_booking_config_from_env() -> Dict[str, str]:
        """Load Vertical Booking configuration from environment variables"""
        return {
            "hotel_id": os.getenv("VERTICAL_BOOKING_HOTEL_ID", ""),
            "style_id": os.getenv("VERTICAL_BOOKING_STYLE_ID", ""),
            "dc": os.getenv("VERTICAL_BOOKING_DC", ""),
            "base_url": os.getenv("VERTICAL_BOOKING_BASE_URL", "https://booking.verticalbooking.com")
        }
    
    @staticmethod
    def get_booking_expert_config_from_env() -> Dict[str, str]:
        """Load Booking Expert configuration from environment variables"""
        return {
            "engine_url": os.getenv("BOOKING_EXPERT_ENGINE_URL", ""),
            "layout_id": os.getenv("BOOKING_EXPERT_LAYOUT_ID", ""),
            "adult_type_id": os.getenv("BOOKING_EXPERT_ADULT_TYPE_ID", ""),
            "teen_type_id": os.getenv("BOOKING_EXPERT_TEEN_TYPE_ID", ""),
            "child_type_id": os.getenv("BOOKING_EXPERT_CHILD_TYPE_ID", "")
        }
    
    @staticmethod
    def get_mcp_config_from_env() -> Dict[str, Any]:
        """Load MCP configuration from environment variables"""
        headers_str = os.getenv("MCP_HEADERS", "{}")
        return {
            "name": os.getenv("MCP_NAME", "default-mcp"),
            "url": os.getenv("MCP_URL", ""),
            "headers": json.loads(headers_str) if headers_str else {}
        }
    
    @staticmethod
    def get_google_sheets_config_from_env() -> Dict[str, str]:
        """Load Google Sheets configuration from environment variables"""
        return {
            "creds_json_path": os.getenv("GOOGLE_SHEETS_CREDS_PATH", ""),
            "sheet_name": os.getenv("GOOGLE_SHEETS_NAME", ""),
            "worksheet_name": os.getenv("GOOGLE_SHEETS_WORKSHEET", "Sheet1")
        }


class IntegrationValidator:
    """Validation utilities for integration configurations"""
    
    @staticmethod
    def validate_shopify_config(config: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Validate Shopify configuration"""
        required = ["shop_url", "admin_api_key"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"
        return True, None
    
    @staticmethod
    def validate_woocommerce_config(config: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Validate WooCommerce configuration"""
        required = ["store_url", "consumer_key", "consumer_secret"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"
        return True, None
    
    @staticmethod
    def validate_magento2_config(config: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Validate Magento2 configuration"""
        required = ["store_url", "consumer_key", "consumer_secret", "access_token", "access_token_secret"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"
        return True, None
    
    @staticmethod
    def validate_prestashop_config(config: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Validate Prestashop configuration"""
        required = ["store_url", "api_key"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"
        return True, None
    
    @staticmethod
    def validate_qapla_config(config: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Validate Qapla configuration"""
        if not config.get("api_key"):
            return False, "Missing required field: api_key"
        return True, None
    
    @staticmethod
    def validate_vertical_booking_config(config: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Validate Vertical Booking configuration"""
        required = ["hotel_id", "style_id", "dc"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"
        return True, None
    
    @staticmethod
    def validate_booking_expert_config(config: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Validate Booking Expert configuration"""
        required = ["engine_url", "layout_id", "adult_type_id", "teen_type_id", "child_type_id"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"
        return True, None
    
    @staticmethod
    def validate_mcp_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate MCP configuration"""
        required = ["name", "url"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"
        return True, None
    
    @staticmethod
    def validate_google_sheets_config(config: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Validate Google Sheets configuration"""
        required = ["creds_json_path", "sheet_name"]
        for field in required:
            if not config.get(field):
                return False, f"Missing required field: {field}"
        return True, None

