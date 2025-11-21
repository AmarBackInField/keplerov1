import requests
from typing import Dict, Optional

class MCPClient:
    """
    Represents a Microservice Client (MCP) integration.
    Allows creating a client, storing its URL and headers, and making requests.
    """

    def __init__(self, name: str, url: str, headers: Optional[Dict[str, str]] = None):
        """
        Initialize the MCP client.

        :param name: Name of the MCP client
        :param url: MCP endpoint URL
        :param headers: Optional headers for requests
        """
        self.name = name
        self.url = url
        self.headers = headers or {}

    def set_header(self, key: str, value: str):
        """Add or update a header"""
        self.headers[key] = value

    def remove_header(self, key: str):
        """Remove a header if exists"""
        if key in self.headers:
            del self.headers[key]

    def make_request(self, method: str = "GET", data: Optional[Dict] = None, params: Optional[Dict] = None):
        """
        Make an HTTP request to the MCP endpoint.

        :param method: HTTP method ("GET", "POST", "PUT", "DELETE")
        :param data: Data to send in body (for POST/PUT)
        :param params: Query parameters (for GET)
        :return: Response object
        """
        method = method.upper()
        try:
            if method == "GET":
                response = requests.get(self.url, headers=self.headers, params=params)
            elif method == "POST":
                response = requests.post(self.url, headers=self.headers, json=data)
            elif method == "PUT":
                response = requests.put(self.url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(self.url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()  # assuming MCP returns JSON
        except requests.exceptions.RequestException as e:
            print(f"Error calling MCP: {e}")
            return None

