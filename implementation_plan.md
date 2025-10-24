# Implementation Plan: Google Sheets to Kommo CRM Order Synchronization

## [Overview]
Implement automated order synchronization from Google Sheets to Kommo CRM, including a sales bot simulator that generates test order data.

This implementation completes the second part of the original technical specification: creating a sales bot simulator that populates Google Sheets with order data, and a synchronization service that reads these orders and adds them as notes to existing Kommo contacts identified by their Telegram ID. The system must be idempotent (avoid duplicating orders), run on a schedule (every 10 seconds for demo), and integrate seamlessly with the existing support bot simulator.

## [Types]
Define data structures for orders and synchronization state tracking.

### Order Data Structure (Dataclass)
```python
@dataclass
class Order:
    telegram_username: str
    telegram_id: str
    date: datetime
    product: str
    amount: float
    currency: str
    payment_status: str  # "paid", "pending", "cancelled"
    
    def to_note_text(self) -> str:
        """Format order as Kommo note text"""
    
    def get_unique_key(self) -> str:
        """Generate unique key for deduplication (date + amount + product + telegram_id)"""
```

### Synchronization State (for tracking processed orders)
```python
@dataclass
class SyncState:
    last_row_processed: int
    last_sync_timestamp: datetime
    total_orders_synced: int
    failed_syncs: List[Dict[str, Any]]
```

## [Files]
Create new files for Google Sheets integration and order synchronization, plus a sales bot simulator.

### New Files to Create:

1. **`src/sheets_client.py`** (250-300 lines)
   - Purpose: Google Sheets API client for reading order data
   - Methods: authenticate(), read_orders(), get_new_rows_since()
   - Dependencies: gspread, oauth2client

2. **`src/order_sync_service.py`** (300-400 lines)
   - Purpose: Core synchronization logic between Sheets and Kommo
   - Methods: sync_orders(), process_order_batch(), deduplicate_orders()
   - Uses: KommoClient, SheetsClient

3. **`demo/sales_bot_simulator.py`** (200-250 lines)
   - Purpose: Simulate sales bot adding orders to Google Sheets
   - Methods: generate_random_order(), populate_sheet(), run_continuous()
   - Creates realistic test data with various products, amounts, statuses

4. **`main.py`** (150-200 lines)
   - Purpose: Main entry point for scheduled synchronization
   - CLI commands: --mode schedule/once, --test, --create-sheet
   - Uses: schedule library for periodic execution

### Existing Files to Modify:

1. **`config.py`** - Already has Google Sheets configuration, no changes needed
2. **`requirements.txt`** - Already has gspread and oauth2client, verified

### Files NOT Modified:
- `src/kommo_client.py` - Already has all needed methods
- `src/logger.py` - Already configured
- `demo/telegram_bot_simulator.py` - Support bot, independent

## [Functions]

### New Functions in `src/sheets_client.py`:

1. **`SheetsClient.__init__(credentials_path, sheet_id, sheet_name, logger)`**
   - Initialize Google Sheets client with service account
   - Authenticate and get worksheet reference
   
2. **`SheetsClient.read_all_orders() -> List[Order]`**
   - Read all rows from sheet
   - Parse into Order objects
   - Validate data formats

3. **`SheetsClient.get_new_rows_since(row_index: int) -> List[Order]`**
   - Read only new rows since last sync
   - For incremental synchronization
   
4. **`SheetsClient.test_connection() -> bool`**
   - Test Google Sheets API connection
   - Verify sheet access

### New Functions in `src/order_sync_service.py`:

1. **`OrderSyncService.__init__(kommo_client, sheets_client, logger)`**
   - Initialize with both API clients
   
2. **`OrderSyncService.sync_orders() -> Dict[str, Any]`**
   - Main synchronization method
   - Returns: {synced: int, skipped: int, errors: List}
   
3. **`OrderSyncService.process_order_batch(orders: List[Order]) -> Dict`**
   - Group orders by telegram_id
   - Find contacts in Kommo
   - Add orders as notes with deduplication
   
4. **`OrderSyncService.deduplicate_orders(contact_id, new_orders) -> List[Order]`**
   - Get existing notes from contact
   - Filter out already synced orders
   - Return only new orders to add

5. **`OrderSyncService.format_order_note(order: Order) -> str`**
   - Format order as Kommo note text
   - Template: "🛍️ Товар: {product}\n💰 Сумма: {amount} {currency}\n..."

### New Functions in `demo/sales_bot_simulator.py`:

1. **`generate_random_order() -> Dict[str, Any]`**
   - Generate realistic order data
   - Random products, amounts (50-5000), currencies, statuses
   
2. **`create_demo_sheet(sheet_name: str) -> str`**
   - Create new Google Sheet
   - Set up headers: telegram_username, telegram_id, date, product, amount, currency, payment_status
   - Return sheet_id
   
3. **`populate_sheet_continuously(sheet_id, interval_seconds)`**
   - Add random orders every N seconds
   - Simulate sales bot behavior
   
4. **`generate_test_data(sheet_id, num_orders: int)`**
   - Generate N test orders at once
   - For initial testing

### New Functions in `main.py`:

1. **`main()`**
   - CLI entry point
   - Parse arguments (--mode, --test, --create-sheet, --version)
   
2. **`run_once()`**
   - Single synchronization run
   - Log results
   
3. **`run_scheduled(interval_seconds: int)`**
   - Schedule periodic synchronization
   - Use schedule library
   - Graceful shutdown on SIGTERM/SIGINT
   
4. **`test_connections()`**
   - Test Kommo API connection
   - Test Google Sheets connection
   - Print status

## [Classes]

### New Classes:

1. **`SheetsClient` (src/sheets_client.py)**
   - Purpose: Google Sheets API wrapper
   - Key Methods: read_all_orders(), get_new_rows_since(), test_connection()
   - Inheritance: None
   - Dependencies: gspread, oauth2client
   
2. **`OrderSyncService` (src/order_sync_service.py)**
   - Purpose: Order synchronization orchestrator
   - Key Methods: sync_orders(), process_order_batch(), deduplicate_orders()
   - Inheritance: None
   - Uses: KommoClient, SheetsClient
   
3. **`Order` (src/order_sync_service.py)**
   - Purpose: Order data model (dataclass)
   - Methods: to_note_text(), get_unique_key()
   - Inheritance: None

### Modified Classes:

None - existing classes (KommoClient, MessageSimulator) remain unchanged.

## [Dependencies]

No new dependencies needed - all already in requirements.txt:

- `gspread==6.1.2` - Google Sheets API client ✅
- `oauth2client==4.1.3` - Google OAuth authentication ✅
- `schedule==1.2.0` - Task scheduling ✅
- `python-dotenv==1.0.0` - Environment variables ✅
- `requests==2.31.0` - HTTP requests ✅
- `colorlog==6.8.0` - Colored logging ✅
- `retrying==1.3.4` - Retry logic ✅

All dependencies already installed and verified.

## [Testing]

Manual testing approach with demo scripts (no unit tests initially).

### Testing Strategy:

1. **Google Sheets Client Testing:**
   - Create test sheet with `demo/sales_bot_simulator.py --create-sheet`
   - Verify sheet reading with `python -c "from src.sheets_client import SheetsClient; ..."`
   - Test data parsing and validation

2. **Order Sync Service Testing:**
   - Run `main.py --mode once` for single sync
   - Verify orders appear in Kommo timeline
   - Check deduplication (run twice, should not duplicate)

3. **Integration Testing:**
   - Run `demo/sales_bot_simulator.py` in background (generates orders)
   - Run `main.py --mode schedule` (syncs every 10 seconds)
   - Run `demo/telegram_bot_simulator.py` (creates contacts)
   - Verify complete flow: contact creation → order generation → sync to Kommo

4. **Edge Case Testing:**
   - Orders for non-existent contacts (should skip gracefully)
   - Malformed data in sheets (should log errors)
   - API rate limits (should retry)
   - Duplicate orders (should deduplicate)

### Test Execution Commands:

```bash
# 1. Create demo sheet and populate with test data
python demo/sales_bot_simulator.py --create-sheet --generate 20

# 2. Test single sync
python main.py --test
python main.py --mode once

# 3. Run continuous demo
# Terminal 1: Generate contacts
python demo/telegram_bot_simulator.py

# Terminal 2: Generate orders
python demo/sales_bot_simulator.py --continuous

# Terminal 3: Sync orders
python main.py --mode schedule
```

## [Implementation Order]

Implement in this specific sequence to ensure working incremental builds:

1. **Create `src/sheets_client.py`**
   - Implement SheetsClient class
   - Test authentication and basic sheet reading
   - Verify data parsing into Order objects

2. **Create `demo/sales_bot_simulator.py`**
   - Implement order generation logic
   - Create sheet creation utility
   - Test writing orders to Google Sheets
   - Generate 20-30 test orders for testing

3. **Create `src/order_sync_service.py`**
   - Implement Order dataclass with methods
   - Implement OrderSyncService with sync logic
   - Test deduplication mechanism
   - Test note formatting

4. **Create `main.py`**
   - Implement CLI argument parsing
   - Implement run_once() mode
   - Test manual sync with test data
   - Verify logs and error handling

5. **Add scheduled mode to `main.py`**
   - Implement run_scheduled() with schedule library
   - Add graceful shutdown (SIGTERM/SIGINT)
   - Test periodic execution (every 10 seconds)

6. **Integration testing**
   - Run all three components together
   - Verify complete flow
   - Check for edge cases and errors
   - Validate idempotency

7. **Final verification**
   - Test with fresh Google Sheet
   - Clean Kommo account test
   - Verify no duplicate orders
   - Check logging completeness
   - Validate all error handling paths

8. **Documentation** (when user requests)
   - Update README.md with complete setup instructions
   - Document all CLI commands
   - Add troubleshooting section
   - Include API references
