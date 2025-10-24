"""
Google Sheets API client for reading order data.
Handles authentication and data retrieval from order sheets.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import gspread
from oauth2client.service_account import ServiceAccountCredentials


class SheetsError(Exception):
    """Base exception for Google Sheets errors."""
    pass


class SheetsAuthError(SheetsError):
    """Authentication errors."""
    pass


class SheetsDataError(SheetsError):
    """Data parsing/validation errors."""
    pass


@dataclass
class Order:
    """
    Order data model.
    
    Attributes:
        telegram_username: Telegram username (e.g., @username)
        telegram_id: Telegram user ID
        date: Order date
        product: Product name
        amount: Order amount
        currency: Currency code (USD, EUR, RUB)
        payment_status: Payment status (paid, pending, cancelled)
    """
    telegram_username: str
    telegram_id: str
    date: datetime
    product: str
    amount: float
    currency: str
    payment_status: str
    
    def to_note_text(self) -> str:
        """
        Format order as Kommo note text.
        
        Returns:
            Formatted note text
        """
        # Format date as readable string
        date_str = self.date.strftime("%d.%m.%Y")
        
        # Emoji based on payment status
        status_emoji = {
            "paid": "✅",
            "pending": "⏳",
            "cancelled": "❌"
        }
        emoji = status_emoji.get(self.payment_status.lower(), "📋")
        
        note_text = (
            f"🛍️ Товар: {self.product}\n"
            f"💰 Сумма: {self.amount} {self.currency}\n"
            f"{emoji} Статус: {self.payment_status}\n"
            f"👤 Telegram: {self.telegram_username} (ID: {self.telegram_id})\n"
            f"📅 Дата: {date_str}"
        )
        
        return note_text
    
    def get_unique_key(self) -> str:
        """
        Generate unique key for deduplication.
        
        Returns:
            Unique identifier string
        """
        # Combine date (day precision), amount, product, and telegram_id
        date_str = self.date.strftime("%Y-%m-%d")
        return f"{self.telegram_id}_{date_str}_{self.amount}_{self.product}"
    
    @classmethod
    def from_row(cls, row: List[str], row_number: int) -> 'Order':
        """
        Parse order from spreadsheet row.
        
        Args:
            row: List of cell values
            row_number: Row number (for error reporting)
            
        Returns:
            Order instance
            
        Raises:
            SheetsDataError: If row data is invalid
        """
        try:
            # Expected columns:
            # telegram_username, telegram_id, date, product, amount, currency, payment_status
            
            if len(row) < 7:
                raise SheetsDataError(
                    f"Row {row_number}: Expected 7 columns, got {len(row)}"
                )
            
            telegram_username = row[0].strip()
            telegram_id = row[1].strip()
            date_str = row[2].strip()
            product = row[3].strip()
            amount_str = row[4].strip()
            currency = row[5].strip()
            payment_status = row[6].strip()
            
            # Validate required fields
            if not telegram_username:
                raise SheetsDataError(f"Row {row_number}: telegram_username is empty")
            
            if not telegram_id:
                raise SheetsDataError(f"Row {row_number}: telegram_id is empty")
            
            if not product:
                raise SheetsDataError(f"Row {row_number}: product is empty")
            
            # Parse date (support multiple formats)
            date = None
            date_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"]
            
            for fmt in date_formats:
                try:
                    date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if date is None:
                raise SheetsDataError(
                    f"Row {row_number}: Invalid date format '{date_str}'. "
                    f"Supported formats: YYYY-MM-DD, DD.MM.YYYY, DD/MM/YYYY"
                )
            
            # Parse amount
            try:
                amount = float(amount_str)
                if amount < 0:
                    raise ValueError("Amount cannot be negative")
            except ValueError as e:
                raise SheetsDataError(
                    f"Row {row_number}: Invalid amount '{amount_str}': {str(e)}"
                )
            
            # Validate currency
            valid_currencies = ["USD", "EUR", "RUB", "GBP", "JPY", "CNY"]
            currency_upper = currency.upper()
            if currency_upper not in valid_currencies:
                raise SheetsDataError(
                    f"Row {row_number}: Invalid currency '{currency}'. "
                    f"Supported: {', '.join(valid_currencies)}"
                )
            
            # Validate payment status
            valid_statuses = ["paid", "pending", "cancelled"]
            status_lower = payment_status.lower()
            if status_lower not in valid_statuses:
                raise SheetsDataError(
                    f"Row {row_number}: Invalid payment status '{payment_status}'. "
                    f"Supported: {', '.join(valid_statuses)}"
                )
            
            return cls(
                telegram_username=telegram_username,
                telegram_id=telegram_id,
                date=date,
                product=product,
                amount=amount,
                currency=currency_upper,
                payment_status=status_lower
            )
            
        except (IndexError, AttributeError) as e:
            raise SheetsDataError(
                f"Row {row_number}: Failed to parse row data: {str(e)}"
            )


class SheetsClient:
    """
    Google Sheets API client.
    
    Attributes:
        credentials_path: Path to service account JSON file
        sheet_id: Google Sheets document ID
        sheet_name: Worksheet/tab name
        logger: Logger instance
        client: Gspread client instance
        sheet: Worksheet instance
    """
    
    # Scopes required for Google Sheets API
    SCOPES = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(
        self,
        credentials_path: str,
        sheet_id: str,
        sheet_name: str,
        logger: logging.Logger
    ):
        """
        Initialize Google Sheets client.
        
        Args:
            credentials_path: Path to service account JSON
            sheet_id: Google Sheets document ID
            sheet_name: Worksheet name
            logger: Logger instance
            
        Raises:
            SheetsAuthError: If authentication fails
        """
        self.credentials_path = credentials_path
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.logger = logger
        
        self.client = None
        self.sheet = None
        
        # Authenticate on initialization
        self._authenticate()
        
        self.logger.info(
            f"Initialized SheetsClient for sheet: {sheet_id}, tab: {sheet_name}"
        )
    
    def _authenticate(self) -> None:
        """
        Authenticate with Google Sheets API.
        
        Raises:
            SheetsAuthError: If authentication fails
        """
        try:
            self.logger.debug("Authenticating with Google Sheets API...")
            
            # Create credentials from service account file
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_path,
                self.SCOPES
            )
            
            # Authorize client
            self.client = gspread.authorize(credentials)
            
            # Open spreadsheet and worksheet
            spreadsheet = self.client.open_by_key(self.sheet_id)
            self.sheet = spreadsheet.worksheet(self.sheet_name)
            
            self.logger.info("Successfully authenticated with Google Sheets API")
            
        except FileNotFoundError:
            error_msg = f"Credentials file not found: {self.credentials_path}"
            self.logger.error(error_msg)
            raise SheetsAuthError(error_msg)
            
        except gspread.exceptions.SpreadsheetNotFound:
            error_msg = f"Spreadsheet not found: {self.sheet_id}"
            self.logger.error(error_msg)
            raise SheetsAuthError(error_msg)
            
        except gspread.exceptions.WorksheetNotFound:
            error_msg = f"Worksheet not found: {self.sheet_name}"
            self.logger.error(error_msg)
            raise SheetsAuthError(error_msg)
            
        except Exception as e:
            error_msg = f"Authentication failed: {str(e)}"
            self.logger.error(error_msg)
            raise SheetsAuthError(error_msg) from e
    
    def test_connection(self) -> bool:
        """
        Test Google Sheets API connection.
        
        Returns:
            True if connection is successful
        """
        try:
            # Try to get sheet title
            title = self.sheet.title
            self.logger.info(f"Connection test successful. Sheet: {title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def read_all_orders(self) -> List[Order]:
        """
        Read all orders from the sheet.
        
        Returns:
            List of Order objects
            
        Raises:
            SheetsError: If reading fails
        """
        self.logger.info("Reading all orders from sheet...")
        
        try:
            # Get all values from sheet
            all_values = self.sheet.get_all_values()
            
            if not all_values:
                self.logger.warning("Sheet is empty")
                return []
            
            # First row is header, skip it
            header = all_values[0]
            data_rows = all_values[1:]
            
            self.logger.debug(f"Found {len(data_rows)} rows (excluding header)")
            
            # Parse rows into Order objects
            orders = []
            errors = []
            
            for idx, row in enumerate(data_rows, start=2):  # Start at 2 (row 1 is header)
                # Skip empty rows
                if not any(cell.strip() for cell in row):
                    self.logger.debug(f"Skipping empty row {idx}")
                    continue
                
                try:
                    order = Order.from_row(row, idx)
                    orders.append(order)
                    
                except SheetsDataError as e:
                    self.logger.warning(str(e))
                    errors.append(str(e))
                    continue
            
            self.logger.info(
                f"Successfully parsed {len(orders)} orders "
                f"({len(errors)} errors)"
            )
            
            return orders
            
        except Exception as e:
            error_msg = f"Failed to read orders: {str(e)}"
            self.logger.error(error_msg)
            raise SheetsError(error_msg) from e
    
    def get_new_rows_since(self, last_row_index: int) -> List[Order]:
        """
        Read only new rows since last sync.
        
        Args:
            last_row_index: Last processed row number (1-indexed)
            
        Returns:
            List of new Order objects
            
        Raises:
            SheetsError: If reading fails
        """
        self.logger.info(f"Reading new rows since row {last_row_index}...")
        
        try:
            # Get all values
            all_values = self.sheet.get_all_values()
            
            if not all_values or len(all_values) <= last_row_index:
                self.logger.info("No new rows found")
                return []
            
            # Get only new rows
            new_rows = all_values[last_row_index:]
            
            self.logger.debug(f"Found {len(new_rows)} new rows")
            
            # Parse new rows
            orders = []
            errors = []
            
            for idx, row in enumerate(new_rows, start=last_row_index + 1):
                # Skip empty rows
                if not any(cell.strip() for cell in row):
                    continue
                
                try:
                    order = Order.from_row(row, idx)
                    orders.append(order)
                    
                except SheetsDataError as e:
                    self.logger.warning(str(e))
                    errors.append(str(e))
                    continue
            
            self.logger.info(
                f"Successfully parsed {len(orders)} new orders "
                f"({len(errors)} errors)"
            )
            
            return orders
            
        except Exception as e:
            error_msg = f"Failed to read new rows: {str(e)}"
            self.logger.error(error_msg)
            raise SheetsError(error_msg) from e
    
    def get_total_rows(self) -> int:
        """
        Get total number of rows in sheet (including header).
        
        Returns:
            Number of rows
        """
        try:
            return len(self.sheet.get_all_values())
        except Exception as e:
            self.logger.error(f"Failed to get row count: {str(e)}")
            return 0
