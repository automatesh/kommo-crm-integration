"""
Order Synchronization Service.
Synchronizes orders from Google Sheets to Kommo CRM timeline.
"""

import logging
from typing import List, Dict, Any, Set
from collections import defaultdict
from datetime import datetime

from src.sheets_client import SheetsClient, Order
from src.kommo_client import KommoClient, KommoContact


class SyncError(Exception):
    """Base exception for synchronization errors."""
    pass


class OrderSyncService:
    """
    Order synchronization orchestrator.
    
    Attributes:
        kommo_client: Kommo API client
        sheets_client: Google Sheets client
        logger: Logger instance
    """
    
    def __init__(
        self,
        kommo_client: KommoClient,
        sheets_client: SheetsClient,
        logger: logging.Logger
    ):
        """
        Initialize order sync service.
        
        Args:
            kommo_client: Initialized Kommo client
            sheets_client: Initialized Sheets client
            logger: Logger instance
        """
        self.kommo_client = kommo_client
        self.sheets_client = sheets_client
        self.logger = logger
        
        self.logger.info("Initialized OrderSyncService")
    
    def sync_orders(self) -> Dict[str, Any]:
        """
        Main synchronization method.
        
        Reads all orders from Google Sheets, groups by telegram_id,
        finds contacts in Kommo, and adds orders as notes with deduplication.
        
        Returns:
            Dictionary with sync results:
            {
                'synced': int,
                'skipped': int,
                'errors': List[str],
                'stats': Dict
            }
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting order synchronization")
        self.logger.info("=" * 60)
        
        results = {
            'synced': 0,
            'skipped': 0,
            'errors': [],
            'stats': {
                'total_orders': 0,
                'unique_contacts': 0,
                'contacts_found': 0,
                'contacts_not_found': 0,
                'duplicates_filtered': 0
            }
        }
        
        try:
            # Read all orders from Google Sheets
            self.logger.info("Reading orders from Google Sheets...")
            orders = self.sheets_client.read_all_orders()
            
            if not orders:
                self.logger.warning("No orders found in Google Sheets")
                return results
            
            results['stats']['total_orders'] = len(orders)
            self.logger.info(f"Found {len(orders)} orders in Google Sheets")
            
            # Group orders by telegram_id
            orders_by_telegram_id = self._group_orders_by_telegram_id(orders)
            results['stats']['unique_contacts'] = len(orders_by_telegram_id)
            
            self.logger.info(
                f"Grouped orders into {len(orders_by_telegram_id)} unique contacts"
            )
            
            # Process each contact's orders
            for telegram_id, contact_orders in orders_by_telegram_id.items():
                try:
                    self.logger.info(f"\nProcessing {len(contact_orders)} orders for Telegram ID: {telegram_id}")
                    
                    # Find contact in Kommo
                    contact = self.kommo_client.find_contact_by_telegram_id(telegram_id)
                    
                    if not contact:
                        self.logger.info(f"Contact not found for Telegram ID: {telegram_id}, creating new contact...")
                        
                        # Get first order to extract contact data
                        first_order = contact_orders[0]
                        
                        # Get custom field IDs
                        telegram_id_field = self.kommo_client.get_custom_field_by_name("Telegram ID")
                        username_field = self.kommo_client.get_custom_field_by_name("Telegram Username")
                        
                        # Build custom fields
                        custom_fields = {}
                        if telegram_id_field:
                            custom_fields[telegram_id_field] = telegram_id
                        if username_field:
                            custom_fields[username_field] = first_order.telegram_username
                        
                        # Create contact
                        try:
                            contact_id = self.kommo_client.create_contact(
                                name=first_order.telegram_username.lstrip('@'),
                                custom_fields=custom_fields
                            )
                            
                            self.logger.info(f"✅ Created new contact: {first_order.telegram_username} (ID: {contact_id})")
                            
                            # Create a minimal contact object
                            from src.kommo_client import KommoContact
                            contact = KommoContact(
                                id=contact_id,
                                name=first_order.telegram_username.lstrip('@'),
                                telegram_id=telegram_id,
                                custom_fields={}
                            )
                            
                        except Exception as e:
                            self.logger.error(f"Failed to create contact: {str(e)}")
                            results['stats']['contacts_not_found'] += 1
                            results['skipped'] += len(contact_orders)
                            results['errors'].append(
                                f"Failed to create contact for Telegram ID {telegram_id}: {str(e)} "
                                f"({len(contact_orders)} orders skipped)"
                            )
                            continue
                    
                    results['stats']['contacts_found'] += 1
                    self.logger.info(f"Found contact: {contact.name} (ID: {contact.id})")
                    
                    # Deduplicate orders
                    new_orders = self._deduplicate_orders(contact.id, contact_orders)
                    
                    duplicates = len(contact_orders) - len(new_orders)
                    if duplicates > 0:
                        self.logger.info(f"Filtered {duplicates} duplicate orders")
                        results['stats']['duplicates_filtered'] += duplicates
                        results['skipped'] += duplicates
                    
                    if not new_orders:
                        self.logger.info("No new orders to sync (all duplicates)")
                        continue
                    
                    # Add new orders as notes AND create leads
                    self.logger.info(f"Adding {len(new_orders)} new orders to timeline...")
                    
                    for order in new_orders:
                        try:
                            # Add note to timeline
                            note_text = self._format_order_note(order)
                            
                            self.kommo_client.add_note_to_contact(
                                contact_id=contact.id,
                                note_text=note_text
                            )
                            
                            # Create lead (deal) for the order
                            lead_name = f"{order.product} - {order.date.strftime('%d.%m.%Y')}"
                            
                            try:
                                lead_id = self.kommo_client.create_lead(
                                    name=lead_name,
                                    price=order.amount,
                                    contact_id=contact.id
                                )
                                self.logger.info(f"  💰 Created lead ID: {lead_id}")
                            except Exception as lead_error:
                                self.logger.warning(f"Failed to create lead: {str(lead_error)}")
                            
                            results['synced'] += 1
                            
                            self.logger.info(
                                f"  ✓ {order.product} - {order.amount} {order.currency} "
                                f"({order.payment_status})"
                            )
                            
                        except Exception as e:
                            error_msg = (
                                f"Failed to add order for {contact.name}: "
                                f"{order.product} - {str(e)}"
                            )
                            self.logger.error(error_msg)
                            results['errors'].append(error_msg)
                            results['skipped'] += 1
                    
                    # Add "Billing" tag to contact with orders
                    try:
                        self.kommo_client.add_tags_to_contact(contact.id, ["Billing"])
                        self.logger.info(f"  🏷️  Added 'Billing' tag to contact")
                    except Exception as tag_error:
                        self.logger.warning(f"Failed to add Billing tag: {str(tag_error)}")
                    
                except Exception as e:
                    error_msg = f"Error processing orders for Telegram ID {telegram_id}: {str(e)}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['skipped'] += len(contact_orders)
            
            # Summary
            self.logger.info("\n" + "=" * 60)
            self.logger.info("Synchronization completed")
            self.logger.info("=" * 60)
            self.logger.info(f"Total orders: {results['stats']['total_orders']}")
            self.logger.info(f"Synced: {results['synced']}")
            self.logger.info(f"Skipped: {results['skipped']}")
            self.logger.info(f"  - Duplicates: {results['stats']['duplicates_filtered']}")
            self.logger.info(f"  - Contacts not found: {results['stats']['contacts_not_found']} contacts")
            self.logger.info(f"Errors: {len(results['errors'])}")
            self.logger.info("=" * 60)
            
            return results
            
        except Exception as e:
            error_msg = f"Synchronization failed: {str(e)}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            raise SyncError(error_msg) from e
    
    def _group_orders_by_telegram_id(
        self,
        orders: List[Order]
    ) -> Dict[str, List[Order]]:
        """
        Group orders by telegram_id.
        
        Args:
            orders: List of Order objects
            
        Returns:
            Dictionary mapping telegram_id to list of orders
        """
        grouped = defaultdict(list)
        
        for order in orders:
            grouped[order.telegram_id].append(order)
        
        return dict(grouped)
    
    def _deduplicate_orders(
        self,
        contact_id: int,
        new_orders: List[Order]
    ) -> List[Order]:
        """
        Filter out already synced orders.
        
        Checks existing notes in contact timeline and filters out
        orders that have already been added.
        
        Args:
            contact_id: Kommo contact ID
            new_orders: List of new orders to check
            
        Returns:
            List of orders that haven't been synced yet
        """
        self.logger.debug(f"Checking for duplicate orders for contact {contact_id}")
        
        try:
            # Get existing notes from contact
            existing_notes = self.kommo_client.get_contact_notes(contact_id)
            
            # Extract unique keys from existing notes
            existing_keys: Set[str] = set()
            
            for note in existing_notes:
                # Try to extract order data from note text
                note_text = note.params.get('text', '')
                
                # Simple check: if note contains product name and amount
                for order in new_orders:
                    if (
                        str(order.product) in note_text and
                        str(order.amount) in note_text and
                        order.date.strftime("%d.%m.%Y") in note_text
                    ):
                        existing_keys.add(order.get_unique_key())
            
            # Filter out duplicates
            unique_orders = [
                order for order in new_orders
                if order.get_unique_key() not in existing_keys
            ]
            
            self.logger.debug(
                f"Found {len(new_orders)} new orders, "
                f"{len(unique_orders)} are unique"
            )
            
            return unique_orders
            
        except Exception as e:
            self.logger.warning(
                f"Failed to check for duplicates: {str(e)}. "
                f"Proceeding with all orders."
            )
            # If we can't check, return all orders (safer than skipping)
            return new_orders
    
    def _format_order_note(self, order: Order) -> str:
        """
        Format order as Kommo note text.
        
        Args:
            order: Order object
            
        Returns:
            Formatted note text
        """
        return order.to_note_text()
    
    def test_connectivity(self) -> Dict[str, bool]:
        """
        Test connectivity to both APIs.
        
        Returns:
            Dictionary with test results:
            {
                'kommo': bool,
                'sheets': bool,
                'overall': bool
            }
        """
        self.logger.info("Testing API connectivity...")
        
        results = {
            'kommo': False,
            'sheets': False,
            'overall': False
        }
        
        # Test Kommo
        try:
            results['kommo'] = self.kommo_client.test_connection()
            if results['kommo']:
                self.logger.info("✓ Kommo API connection successful")
            else:
                self.logger.error("✗ Kommo API connection failed")
        except Exception as e:
            self.logger.error(f"✗ Kommo API connection error: {str(e)}")
            results['kommo'] = False
        
        # Test Google Sheets
        try:
            results['sheets'] = self.sheets_client.test_connection()
            if results['sheets']:
                self.logger.info("✓ Google Sheets API connection successful")
            else:
                self.logger.error("✗ Google Sheets API connection failed")
        except Exception as e:
            self.logger.error(f"✗ Google Sheets API connection error: {str(e)}")
            results['sheets'] = False
        
        # Overall
        results['overall'] = results['kommo'] and results['sheets']
        
        if results['overall']:
            self.logger.info("✓ All API connections successful")
        else:
            self.logger.error("✗ Some API connections failed")
        
        return results
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """
        Get current synchronization statistics.
        
        Returns:
            Dictionary with stats:
            {
                'total_orders_in_sheet': int,
                'total_contacts_in_kommo': int,
                'sheet_last_updated': str
            }
        """
        stats = {}
        
        try:
            # Google Sheets stats
            total_rows = self.sheets_client.get_total_rows()
            stats['total_orders_in_sheet'] = max(0, total_rows - 1)  # Exclude header
            
            # Kommo stats (just test connection)
            account_info = self.kommo_client.get_account_info()
            stats['kommo_account'] = account_info.get('name', 'Unknown')
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get sync stats: {str(e)}")
            return {}
