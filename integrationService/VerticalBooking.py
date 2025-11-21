import requests
from typing import Dict, Any, Optional


class VerticalBookingClient:
    """
    Lightweight Python client for Vertical Booking integration.
    Supports generating pre-filled booking links for hotels.
    """

    def __init__(self, hotel_id: str, style_id: str, dc: str, base_url: str = "https://booking.verticalbooking.com"):
        """
        Initialize Vertical Booking Client.

        :param hotel_id: Hotel ID
        :param style_id: Style ID
        :param dc: Distribution Channel or DC code
        :param base_url: Base Vertical Booking URL
        """
        self.hotel_id = hotel_id
        self.style_id = style_id
        self.dc = dc
        self.base_url = base_url.rstrip("/")

    def generate_booking_link(
        self,
        check_in: str,
        check_out: str,
        adults: int = 1,
        children: int = 0,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a pre-filled booking link.

        :param check_in: Check-in date (YYYY-MM-DD)
        :param check_out: Check-out date (YYYY-MM-DD)
        :param adults: Number of adults
        :param children: Number of children
        :param extra_params: Additional query parameters as a dict
        :return: URL string
        """
        params = {
            "hotel": self.hotel_id,
            "style": self.style_id,
            "dc": self.dc,
            "checkin": check_in,
            "checkout": check_out,
            "adults": adults,
            "children": children
        }

        if extra_params:
            params.update(extra_params)

        # Build query string
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        return f"{self.base_url}/book?{query_string}"

    def test_connection(self) -> bool:
        """
        Basic test to check if the Vertical Booking URL is reachable.
        """
        try:
            response = requests.get(self.base_url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
