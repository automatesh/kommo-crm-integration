#!/usr/bin/env python3
"""
Unified Demo Runner for Kommo CRM Integration.
Runs all three modules in a single process with periodic execution.
"""

import sys
import os
import time
import signal
import random
from datetime import datetime
from threading import Thread, Event

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.kommo_client import KommoClient
from src.sheets_client import SheetsClient
from src.order_sync_service import OrderSyncService
from src.message_simulator import MessageSimulator
from src.logger import setup_logger
from config import Config

# Import generator functions
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Global shutdown event
shutdown_event = Event()

# Contact pool for telegram bot
CONTACT_NAMES = [
    "Иван Петров", "Мария Смирнова", "Алексей Козлов", "Елена Волкова",
    "Дмитрий Соколов", "Анна Морозова", "Сергей Новиков", "Ольга Федорова",
    "Андрей Михайлов", "Татьяна Попова"
]

ACTIVE_CONTACTS = []

def signal_handler(sig, frame):
    """Handle CTRL+C gracefully."""
    print("\n\n🛑 Shutting down demo runner...")
    shutdown_event.set()


def create_contacts_worker(kommo_client, message_simulator, logger, interval=15):
    """
    Worker thread: Create 1-2 contacts periodically.
    
    Args:
        kommo_client: Kommo API client
        message_simulator: Message simulator
        logger: Logger instance
        interval: Interval in seconds between generations
    """
    contact_count = 0
    
    logger.info("🤖 Contact generator started")
    
    while not shutdown_event.is_set():
        try:
            # Generate 1-2 contacts
            num_contacts = random.randint(1, 2)
            
            for _ in range(num_contacts):
                if not CONTACT_NAMES:
                    break
                
                # Get random name
                name = CONTACT_NAMES.pop(0)
                
                # Generate Telegram data
                username = "@" + name.lower().replace(" ", "_")
                telegram_id = str(random.randint(100001, 100010))
                
                # Get custom field IDs
                telegram_id_field = kommo_client.get_custom_field_by_name("Telegram ID")
                username_field = kommo_client.get_custom_field_by_name("Telegram Username")
                
                # Create contact
                custom_fields = {}
                if telegram_id_field:
                    custom_fields[telegram_id_field] = telegram_id
                if username_field:
                    custom_fields[username_field] = username
                
                contact_id = kommo_client.create_contact(
                    name=name,
                    custom_fields=custom_fields
                )
                
                contact_count += 1
                
                # Add conversation
                conversation = message_simulator.generate_conversation(
                    contact_name=name,
                    telegram_username=username,
                    conversation_type=random.choice(["support", "docs", "refund"]),
                    num_exchanges=random.randint(2, 4)
                )
                
                for message in conversation:
                    direction = "👤 Клиент" if message.is_incoming else "👨‍💼 Поддержка"
                    note_text = f"{direction}: {message.text}"
                    kommo_client.add_note_to_contact(contact_id, note_text)
                
                # Add tags
                tags = list(set(tag.value for msg in conversation for tag in msg.tags))
                if tags:
                    kommo_client.add_tags_to_contact(contact_id, tags)
                
                ACTIVE_CONTACTS.append({
                    "id": contact_id,
                    "name": name,
                    "username": username,
                    "telegram_id": telegram_id
                })
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"[{timestamp}] 👤 Created contact: {name} (Telegram ID: {telegram_id})")
            
            # Wait for next interval
            shutdown_event.wait(timeout=interval)
            
        except Exception as e:
            logger.error(f"Contact generator error: {str(e)}")
            shutdown_event.wait(timeout=5)
    
    logger.info(f"Contact generator stopped. Total created: {contact_count}")


def create_orders_worker(sheets_client, logger, interval=12):
    """
    Worker thread: Create 1-2 orders in Google Sheets periodically.
    
    Args:
        sheets_client: Google Sheets client
        logger: Logger instance
        interval: Interval in seconds between generations
    """
    order_count = 0
    
    # Products catalog
    PRODUCTS = [
        "Premium Subscription", "Basic Subscription", "Pro Account", "API Access",
        "Consultation Hour", "Training Course", "Technical Support Package",
        "Custom Integration", "Advanced Features Pack"
    ]
    
    logger.info("🛍️ Order generator started")
    
    # Get worksheet
    try:
        worksheet = sheets_client.sheet
    except Exception as e:
        logger.error(f"Failed to get worksheet: {str(e)}")
        return
    
    while not shutdown_event.is_set():
        try:
            # Generate 1-2 orders
            num_orders = random.randint(1, 2)
            
            for _ in range(num_orders):
                # Random Telegram ID (100001-100010)
                telegram_id = str(random.randint(100001, 100010))
                username = f"@user_{telegram_id}"
                
                # Random order data
                date = datetime.now().strftime("%Y-%m-%d")
                product = random.choice(PRODUCTS)
                amount = round(random.uniform(50, 5000), 2)
                currency = random.choice(["USD", "EUR", "RUB"])
                status = random.choices(
                    ["paid", "pending", "cancelled"],
                    weights=[70, 20, 10],
                    k=1
                )[0]
                
                # Add to sheet
                row = [username, telegram_id, date, product, str(amount), currency, status]
                worksheet.append_row(row)
                
                order_count += 1
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                status_emoji = {"paid": "✅", "pending": "⏳", "cancelled": "❌"}
                emoji = status_emoji.get(status, "📋")
                print(f"[{timestamp}] 🛍️ Created order: {product} - {amount} {currency} {emoji}")
            
            # Wait for next interval
            shutdown_event.wait(timeout=interval)
            
        except Exception as e:
            logger.error(f"Order generator error: {str(e)}")
            shutdown_event.wait(timeout=5)
    
    logger.info(f"Order generator stopped. Total created: {order_count}")


def sync_worker(sync_service, logger, interval=20):
    """
    Worker thread: Synchronize orders from Google Sheets to Kommo.
    
    Args:
        sync_service: Order sync service
        logger: Logger instance
        interval: Interval in seconds between syncs
    """
    sync_count = 0
    
    logger.info("🔄 Sync worker started")
    
    while not shutdown_event.is_set():
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{timestamp}] 🔄 Running synchronization...")
            
            results = sync_service.sync_orders()
            
            sync_count += 1
            
            print(f"[{timestamp}] ✓ Sync #{sync_count}: "
                  f"{results['synced']} synced, "
                  f"{results['skipped']} skipped")
            
            # Wait for next interval
            shutdown_event.wait(timeout=interval)
            
        except Exception as e:
            logger.error(f"Sync worker error: {str(e)}")
            shutdown_event.wait(timeout=5)
    
    logger.info(f"Sync worker stopped. Total syncs: {sync_count}")


def main():
    """Main demo runner."""
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load configuration
        config = Config.from_env()
        logger = setup_logger(
            name="demo-runner",
            log_level=config.log_level,
            log_file_path=config.log_file_path
        )
        
        print("=" * 70)
        print("🚀 Kommo CRM Integration - Full Demo Runner")
        print("=" * 70)
        print("This demo runs 3 modules simultaneously:")
        print("  1. 👤 Contact Generator (Telegram Bot Simulator)")
        print("  2. 🛍️  Order Generator (Sales Bot Simulator)")
        print("  3. 🔄 Order Synchronization (Google Sheets → Kommo)")
        print("=" * 70)
        print("\nPress CTRL+C to stop\n")
        
        # Initialize API clients
        logger.info("Initializing API clients...")
        
        kommo_client = KommoClient(
            subdomain=config.kommo_subdomain,
            access_token=config.kommo_access_token,
            logger=logger
        )
        
        sheets_client = SheetsClient(
            credentials_path=config.google_credentials_path,
            sheet_id=config.google_sheet_id,
            sheet_name=config.google_sheet_name,
            logger=logger
        )
        
        sync_service = OrderSyncService(
            kommo_client=kommo_client,
            sheets_client=sheets_client,
            logger=logger
        )
        
        message_simulator = MessageSimulator(logger)
        
        logger.info("✓ All clients initialized")
        
        # Start worker threads
        threads = []
        
        # Contact generator (every 15 seconds, creates 1-2 contacts)
        contact_thread = Thread(
            target=create_contacts_worker,
            args=(kommo_client, message_simulator, logger, 15),
            daemon=True
        )
        contact_thread.start()
        threads.append(contact_thread)
        
        # Order generator (every 12 seconds, creates 1-2 orders)
        order_thread = Thread(
            target=create_orders_worker,
            args=(sheets_client, logger, 12),
            daemon=True
        )
        order_thread.start()
        threads.append(order_thread)
        
        # Sync worker (every 20 seconds)
        sync_thread = Thread(
            target=sync_worker,
            args=(sync_service, logger, 20),
            daemon=True
        )
        sync_thread.start()
        threads.append(sync_thread)
        
        print("✓ All workers started!\n")
        
        # Main loop - wait for shutdown
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=1)
        
        # Wait for threads to finish
        print("\nWaiting for workers to finish...")
        for thread in threads:
            thread.join(timeout=3)
        
        print("\n" + "=" * 70)
        print("✓ Demo runner stopped successfully")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
