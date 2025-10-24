#!/usr/bin/env python3
"""
Create custom fields in Kommo for Telegram integration.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kommo_client import KommoClient
from src.logger import setup_logger_from_config
from config import Config

def create_custom_fields():
    """Create necessary custom fields in Kommo."""
    
    config = Config.from_env()
    logger = setup_logger_from_config('create_fields', config)
    
    client = KommoClient(
        subdomain=config.kommo_subdomain,
        access_token=config.kommo_access_token,
        logger=logger
    )
    
    print("=" * 60)
    print("Creating Custom Fields in Kommo")
    print("=" * 60)
    
    # Check existing fields
    existing_fields = client.get_custom_fields()
    existing_names = [f['name'] for f in existing_fields]
    
    print(f"\nExisting fields: {existing_names}\n")
    
    # Fields to create
    fields_to_create = [
        {
            "name": "Telegram Username",
            "type": "text",
            "code": "TELEGRAM_USERNAME"
        },
        {
            "name": "First Contact Date",
            "type": "date",
            "code": "FIRST_CONTACT_DATE"
        },
        {
            "name": "Chat Link",
            "type": "url",
            "code": "CHAT_LINK"
        }
    ]
    
    for field_data in fields_to_create:
        if field_data["name"] in existing_names:
            print(f"✓ Field '{field_data['name']}' already exists")
            continue
        
        try:
            # Create custom field
            payload = [field_data]
            
            response = client._make_request(
                'POST',
                '/api/v4/contacts/custom_fields',
                data=payload
            )
            
            print(f"✅ Created field: {field_data['name']}")
            print(f"   Response: {response}")
            
        except Exception as e:
            print(f"✗ Failed to create field '{field_data['name']}': {str(e)}")
    
    # Refresh and show all fields
    print("\n" + "=" * 60)
    print("All Custom Fields:")
    print("=" * 60)
    
    all_fields = client.get_custom_fields()
    for field in all_fields:
        print(f"  • {field.get('name')} (ID: {field.get('id')}, Type: {field.get('type')})")
    
    print("\n✓ Done!")


if __name__ == '__main__':
    create_custom_fields()
