#!/usr/bin/env python3
"""
Kommo CRM - Google Sheets Order Synchronization
Main entry point for scheduled synchronization.
"""

import sys
import signal
import argparse
import time
from datetime import datetime
from typing import Optional

import schedule

from config import Config, ConfigError
from src.logger import setup_logger_from_config
from src.kommo_client import KommoClient
from src.sheets_client import SheetsClient
from src.order_sync_service import OrderSyncService

# Version
VERSION = "1.0.0"

# Global flag for graceful shutdown
running = True


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    print("\n\n🛑 Shutting down gracefully...")
    running = False


def test_connections(config: Config, logger) -> bool:
    """
    Test API connections.
    
    Args:
        config: Application configuration
        logger: Logger instance
        
    Returns:
        True if all connections successful
    """
    print("\n" + "=" * 60)
    print("🔌 Testing API Connections")
    print("=" * 60)
    
    try:
        # Initialize clients
        print("\n📡 Initializing API clients...")
        
        kommo_client = KommoClient(
            subdomain=config.kommo_subdomain,
            access_token=config.kommo_access_token,
            logger=logger,
            retry_attempts=config.retry_attempts,
            retry_delay=config.retry_delay_seconds
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
        
        # Test connectivity
        results = sync_service.test_connectivity()
        
        print("\n" + "=" * 60)
        print("📊 Test Results")
        print("=" * 60)
        print(f"Kommo CRM:      {'✓ Connected' if results['kommo'] else '✗ Failed'}")
        print(f"Google Sheets:  {'✓ Connected' if results['sheets'] else '✗ Failed'}")
        print("=" * 60)
        
        if results['overall']:
            print("\n✅ All connections successful!\n")
            
            # Show stats
            stats = sync_service.get_sync_stats()
            if stats:
                print("📈 Statistics:")
                print(f"  - Kommo Account: {stats.get('kommo_account', 'N/A')}")
                print(f"  - Orders in Sheet: {stats.get('total_orders_in_sheet', 0)}")
                print()
            
            return True
        else:
            print("\n❌ Some connections failed. Check configuration.\n")
            return False
            
    except Exception as e:
        print(f"\n❌ Connection test failed: {str(e)}\n")
        logger.error(f"Connection test error: {str(e)}")
        return False


def run_once(config: Config, logger) -> bool:
    """
    Perform single synchronization run.
    
    Args:
        config: Application configuration
        logger: Logger instance
        
    Returns:
        True if sync successful
    """
    logger.info("Starting single synchronization run")
    
    try:
        # Initialize clients
        kommo_client = KommoClient(
            subdomain=config.kommo_subdomain,
            access_token=config.kommo_access_token,
            logger=logger,
            retry_attempts=config.retry_attempts,
            retry_delay=config.retry_delay_seconds
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
        
        # Perform synchronization
        results = sync_service.sync_orders()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Synchronization Summary")
        print("=" * 60)
        print(f"Total orders:   {results['stats']['total_orders']}")
        print(f"Synced:         {results['synced']} ✓")
        print(f"Skipped:        {results['skipped']}")
        print(f"  - Duplicates: {results['stats']['duplicates_filtered']}")
        print(f"  - Not found:  {results['stats']['contacts_not_found']} contacts")
        print(f"Errors:         {len(results['errors'])}")
        print("=" * 60)
        
        if results['errors']:
            print("\n⚠️  Errors:")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(results['errors']) > 5:
                print(f"  ... and {len(results['errors']) - 5} more")
        
        print()
        
        return len(results['errors']) == 0
        
    except Exception as e:
        logger.error(f"Synchronization failed: {str(e)}")
        print(f"\n❌ Synchronization failed: {str(e)}\n")
        return False


def run_scheduled(config: Config, logger) -> None:
    """
    Run synchronization on schedule.
    
    Args:
        config: Application configuration
        logger: Logger instance
    """
    global running
    
    interval = config.sync_interval_seconds
    
    print("\n" + "=" * 60)
    print("⏰ Scheduled Synchronization Mode")
    print("=" * 60)
    print(f"Interval: {interval} seconds")
    print(f"Press CTRL+C to stop")
    print("=" * 60)
    
    # Initialize clients once
    logger.info("Initializing API clients for scheduled sync...")
    
    try:
        kommo_client = KommoClient(
            subdomain=config.kommo_subdomain,
            access_token=config.kommo_access_token,
            logger=logger,
            retry_attempts=config.retry_attempts,
            retry_delay=config.retry_delay_seconds
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
        
        logger.info("API clients initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize clients: {str(e)}")
        print(f"\n❌ Initialization failed: {str(e)}\n")
        return
    
    # Define sync job
    def sync_job():
        """Job to run on schedule."""
        if not running:
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{timestamp}] 🔄 Starting scheduled sync...")
        
        try:
            results = sync_service.sync_orders()
            
            print(f"[{timestamp}] ✓ Sync complete: "
                  f"{results['synced']} synced, "
                  f"{results['skipped']} skipped")
            
        except Exception as e:
            logger.error(f"Scheduled sync failed: {str(e)}")
            print(f"[{timestamp}] ✗ Sync failed: {str(e)}")
    
    # Schedule job
    schedule.every(interval).seconds.do(sync_job)
    
    # Run first sync immediately
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Running initial sync...\n")
    sync_job()
    
    # Main loop
    try:
        while running:
            schedule.run_pending()
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    
    finally:
        print("\n" + "=" * 60)
        print("✓ Synchronization stopped gracefully")
        print("=" * 60)
        logger.info("Scheduled synchronization stopped")


def main():
    """Main entry point."""
    global running
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Kommo CRM - Google Sheets Order Synchronization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode once           # Run single sync
  %(prog)s --mode schedule       # Run scheduled sync (every N seconds)
  %(prog)s --test                # Test API connections
  %(prog)s --version             # Show version
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['once', 'schedule'],
        help='Sync mode: once (single run) or schedule (periodic)'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test API connections and exit'
    )
    
    parser.add_argument(
        '--version',
        action='store_true',
        help='Show version and exit'
    )
    
    args = parser.parse_args()
    
    # Show version
    if args.version:
        print(f"Kommo CRM - Google Sheets Sync v{VERSION}")
        return 0
    
    # Load configuration
    try:
        config = Config.from_env()
    except ConfigError as e:
        print(f"\n❌ Configuration error:\n{str(e)}\n")
        return 1
    
    # Setup logger
    logger = setup_logger_from_config('kommo-sync', config)
    logger.info(f"Starting Kommo Sync v{VERSION}")
    logger.info(f"Configuration: {config}")
    
    # Test connections
    if args.test:
        success = test_connections(config, logger)
        return 0 if success else 1
    
    # Run sync
    if args.mode == 'once':
        success = run_once(config, logger)
        return 0 if success else 1
    
    elif args.mode == 'schedule':
        run_scheduled(config, logger)
        return 0
    
    else:
        # No mode specified
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
