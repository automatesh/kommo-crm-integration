#!/usr/bin/env python3
"""
Sales Bot Simulator for Google Sheets.
Simulates a Telegram sales bot that writes order data to Google Sheets.
"""

import sys
import os
import time
import signal
import random
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from src.logger import setup_logger_from_config
from config import Config

# Global flag for graceful shutdown
running = True

# Product catalog for realistic orders
PRODUCTS = [
    "Premium Subscription",
    "Basic Subscription",
    "Pro Account",
    "API Access",
    "Consultation Hour",
    "Training Course",
    "Technical Support Package",
    "Custom Integration",
    "Advanced Features Pack",
    "Enterprise License",
    "Mobile App Access",
    "Data Analytics Module",
    "Automation Bundle",
    "White Label Solution",
    "Priority Support"
]

# Telegram usernames pool (will be matched with support bot contacts)
TELEGRAM_USERS = [
    {"username": "@ivan_petrov", "id": "100001"},
    {"username": "@maria_smirnova", "id": "100002"},
    {"username": "@alex_kozlov", "id": "100003"},
    {"username": "@elena_volkova", "id": "100004"},
    {"username": "@dmitry_sokolov", "id": "100005"},
    {"username": "@anna_morozova", "id": "100006"},
    {"username": "@sergey_novikov", "id": "100007"},
    {"username": "@olga_fedorova", "id": "100008"},
    {"username": "@andrey_mikhaylov", "id": "100009"},
    {"username": "@tatyana_popova", "id": "100010"}
]


def signal_handler(sig, frame):
    """Handle CTRL+C gracefully."""
    global running
    print("\n\n🛑 Stopping sales bot simulator...")
    running = False


def authenticate_sheets(credentials_path: str) -> gspread.Client:
    """
    Authenticate with Google Sheets API.
    
    Args:
        credentials_path: Path to service account JSON
        
    Returns:
        Authenticated gspread client
    """
    scopes = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        credentials_path,
        scopes
    )
    
    return gspread.authorize(credentials)


def create_demo_sheet(
    client: gspread.Client,
    sheet_name: str = "Kommo Demo Orders"
) -> str:
    """
    Create new Google Sheet for orders.
    
    Args:
        client: Authenticated gspread client
        sheet_name: Name for the new spreadsheet
        
    Returns:
        Sheet ID
    """
    print(f"\n📋 Creating new spreadsheet: {sheet_name}...")
    
    # Create new spreadsheet
    spreadsheet = client.create(sheet_name)
    sheet_id = spreadsheet.id
    
    # Get the first (default) worksheet
    worksheet = spreadsheet.sheet1
    worksheet.update_title("Orders")
    
    # Set up headers
    headers = [
        "telegram_username",
        "telegram_id",
        "date",
        "product",
        "amount",
        "currency",
        "payment_status"
    ]
    
    worksheet.update('A1:G1', [headers])
    
    # Format header row (bold)
    worksheet.format('A1:G1', {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
    })
    
    print(f"✅ Created spreadsheet with ID: {sheet_id}")
    print(f"📝 Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    
    return sheet_id


def generate_random_order() -> Dict[str, Any]:
    """
    Generate realistic random order data.
    
    Returns:
        Dictionary with order data
    """
    # Random user
    user = random.choice(TELEGRAM_USERS)
    
    # Random date within last 30 days
    days_ago = random.randint(0, 30)
    order_date = datetime.now() - timedelta(days=days_ago)
    date_str = order_date.strftime("%Y-%m-%d")
    
    # Random product
    product = random.choice(PRODUCTS)
    
    # Random amount (50 to 5000)
    amount = round(random.uniform(50, 5000), 2)
    
    # Random currency
    currency = random.choice(["USD", "EUR", "RUB"])
    
    # Payment status (weighted - more paid than pending/cancelled)
    status = random.choices(
        ["paid", "pending", "cancelled"],
        weights=[70, 20, 10],
        k=1
    )[0]
    
    return {
        "telegram_username": user["username"],
        "telegram_id": user["id"],
        "date": date_str,
        "product": product,
        "amount": amount,
        "currency": currency,
        "payment_status": status
    }


def add_order_to_sheet(worksheet: gspread.Worksheet, order: Dict[str, Any]) -> None:
    """
    Add single order to the sheet.
    
    Args:
        worksheet: Google Sheets worksheet
        order: Order data dictionary
    """
    row = [
        order["telegram_username"],
        order["telegram_id"],
        order["date"],
        order["product"],
        str(order["amount"]),
        order["currency"],
        order["payment_status"]
    ]
    
    worksheet.append_row(row)


def generate_test_data(
    sheet_id: str,
    credentials_path: str,
    num_orders: int = 20
) -> None:
    """
    Generate multiple test orders at once.
    
    Args:
        sheet_id: Google Sheets ID
        credentials_path: Path to credentials JSON
        num_orders: Number of orders to generate
    """
    print(f"\n📦 Generating {num_orders} test orders...")
    
    # Authenticate
    client = authenticate_sheets(credentials_path)
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet("Orders")
    
    # Generate and add orders
    for i in range(num_orders):
        order = generate_random_order()
        add_order_to_sheet(worksheet, order)
        
        status_emoji = {"paid": "✅", "pending": "⏳", "cancelled": "❌"}
        emoji = status_emoji.get(order["payment_status"], "📋")
        
        print(f"  {i+1}/{num_orders} {emoji} {order['product']}: "
              f"{order['amount']} {order['currency']} "
              f"({order['telegram_username']})")
    
    print(f"\n✅ Generated {num_orders} orders successfully!")


def run_continuous(
    sheet_id: str,
    credentials_path: str,
    interval_seconds: int = 5
) -> None:
    """
    Continuously generate orders.
    
    Args:
        sheet_id: Google Sheets ID
        credentials_path: Path to credentials JSON
        interval_seconds: Interval between orders
    """
    global running
    
    print("=" * 60)
    print("🤖 Sales Bot Simulator for Google Sheets")
    print("=" * 60)
    print(f"Sheet ID: {sheet_id}")
    print(f"Interval: {interval_seconds} seconds")
    print("=" * 60)
    print("\n🚀 Starting continuous order generation... (Press CTRL+C to stop)\n")
    
    # Authenticate
    client = authenticate_sheets(credentials_path)
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet("Orders")
    
    order_count = 0
    
    try:
        while running:
            # Generate random order
            order = generate_random_order()
            
            # Add to sheet
            add_order_to_sheet(worksheet, order)
            order_count += 1
            
            # Display status
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            status_emoji = {"paid": "✅", "pending": "⏳", "cancelled": "❌"}
            emoji = status_emoji.get(order["payment_status"], "📋")
            
            print(f"[{timestamp}] {emoji} Order #{order_count}: "
                  f"{order['product']} - {order['amount']} {order['currency']}")
            print(f"   👤 {order['telegram_username']} (ID: {order['telegram_id']})")
            print(f"   ⏱️  Next order in {interval_seconds} seconds...\n")
            
            # Wait
            if running:
                time.sleep(interval_seconds)
        
        # Graceful shutdown
        print("\n" + "=" * 60)
        print("✓ Sales bot simulator stopped gracefully")
        print(f"Total orders generated: {order_count}")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        print(f"Total orders generated: {order_count}")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """CLI for sales bot simulator."""
    global running
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(
        description="Sales Bot Simulator - Generate order data in Google Sheets"
    )
    
    parser.add_argument(
        '--create-sheet',
        action='store_true',
        help='Create new demo sheet'
    )
    
    parser.add_argument(
        '--sheet-name',
        type=str,
        default='Kommo Demo Orders',
        help='Name for new sheet (used with --create-sheet)'
    )
    
    parser.add_argument(
        '--sheet-id',
        type=str,
        help='Existing sheet ID to use'
    )
    
    parser.add_argument(
        '--generate',
        type=int,
        metavar='N',
        help='Generate N test orders at once'
    )
    
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuous order generation'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Interval between orders in seconds (default: 5)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load config
        config = Config.from_env()
        credentials_path = config.google_credentials_path
        
        # Authenticate
        client = authenticate_sheets(credentials_path)
        
        # Create sheet if requested
        if args.create_sheet:
            sheet_id = create_demo_sheet(client, args.sheet_name)
            print(f"\n💡 Add this to your .env file:")
            print(f"GOOGLE_SHEET_ID={sheet_id}")
            
            # If no other action, just exit
            if not args.generate and not args.continuous:
                return 0
        
        # Get sheet ID
        sheet_id = args.sheet_id or config.google_sheet_id
        
        if not sheet_id:
            print("✗ Error: No sheet ID provided!")
            print("Use --sheet-id <ID> or set GOOGLE_SHEET_ID in .env")
            print("Or use --create-sheet to create a new sheet")
            return 1
        
        # Generate test data
        if args.generate:
            generate_test_data(sheet_id, credentials_path, args.generate)
        
        # Run continuous
        elif args.continuous:
            run_continuous(sheet_id, credentials_path, args.interval)
        
        # No action specified
        else:
            parser.print_help()
            return 1
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
