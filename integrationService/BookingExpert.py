import requests
from typing import Dict, Any, Optional


class BookingExpertClient:
    """
    Lightweight Python client for Booking Expert integration.
    Supports generating pre-filled booking links for customers.
    """

    def __init__(
        self,
        engine_url: str,
        layout_id: str,
        adult_type_id: str,
        teen_type_id: str,
        child_type_id: str
    ):
        """
        Initialize Booking Expert Client.

        :param engine_url: Booking Expert engine URL
        :param layout_id: Layout ID for bookings
        :param adult_type_id: ID for adult guest type
        :param teen_type_id: ID for teen guest type
        :param child_type_id: ID for child guest type
        """
        self.engine_url = engine_url.rstrip("/")
        self.layout_id = layout_id
        self.adult_type_id = adult_type_id
        self.teen_type_id = teen_type_id
        self.child_type_id = child_type_id

    def generate_booking_link(
        self,
        hotel_id: str,
        check_in: str,
        check_out: str,
        adults: int = 1,
        teens: int = 0,
        children: int = 0,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a pre-filled booking link.

        :param hotel_id: Hotel ID for the booking
        :param check_in: Check-in date (YYYY-MM-DD)
        :param check_out: Check-out date (YYYY-MM-DD)
        :param adults: Number of adults
        :param teens: Number of teens
        :param children: Number of children
        :param extra_params: Additional query parameters as a dict
        :return: URL string
        """
        params = {
            "layout": self.layout_id,
            "hotel": hotel_id,
            "checkin": check_in,
            "checkout": check_out,
            f"guests[{self.adult_type_id}]": adults,
            f"guests[{self.teen_type_id}]": teens,
            f"guests[{self.child_type_id}]": children,
        }

        if extra_params:
            params.update(extra_params)

        # Build query string
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        return f"{self.engine_url}?{query_string}"

    def test_connection(self) -> bool:
        """
        Basic test to see if engine URL is reachable.
        """
        try:
            response = requests.get(self.engine_url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
