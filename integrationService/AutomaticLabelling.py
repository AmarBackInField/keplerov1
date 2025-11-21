import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any


class KeplerGoogleSheet:
    """
    Client to integrate Kepler AI with Google Sheets.
    Allows saving conversation data into a spreadsheet.
    """

    def __init__(self, creds_json_path: str, sheet_name: str, worksheet_name: str = "Sheet1"):
        """
        Initialize the Google Sheet client.

        :param creds_json_path: Path to Google service account JSON file
        :param sheet_name: Name of the Google Sheet
        :param worksheet_name: Name of the worksheet (default: "Sheet1")
        """
        self.creds = Credentials.from_service_account_file(
            creds_json_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"]
        )
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open(sheet_name).worksheet(worksheet_name)

    def append_row(self, row_data: List[Any]):
        """
        Append a single row of data to the sheet.

        :param row_data: List of values corresponding to the columns
        """
        self.sheet.append_row(row_data)

    def append_rows(self, rows_data: List[List[Any]]):
        """
        Append multiple rows to the sheet.

        :param rows_data: List of rows, where each row is a list of column values
        """
        for row in rows_data:
            self.append_row(row)

    def update_cell(self, row: int, col: int, value: Any):
        """
        Update a specific cell.

        :param row: Row number (1-indexed)
        :param col: Column number (1-indexed)
        :param value: Value to write
        """
        self.sheet.update_cell(row, col, value)

    def get_all_records(self) -> List[Dict[str, Any]]:
        """
        Get all rows as a list of dictionaries.

        :return: List of dicts where keys are column headers
        """
        return self.sheet.get_all_records()