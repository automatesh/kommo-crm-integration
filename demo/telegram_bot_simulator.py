#!/usr/bin/env python3
"""
Telegram Bot Simulator for Kommo CRM.
Simulates incoming messages from Telegram bot, creating contacts and conversations directly in Kommo.
"""

import sys
import os
import time
import signal
import random
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kommo_client import KommoClient
from src.message_simulator import MessageSimulator, ContactTag
from src.logger import setup_logger_from_config
from config import Config

# Global flag for graceful shutdown
running = True

# Dynamic contact pool
ACTIVE_CONTACTS = []

# Names pool for new contacts
CONTACT_NAMES = [
    "Иван Петров", "Мария Смирнова", "Алексей Козлов", "Елена Волкова",
    "Дмитрий Соколов", "Анна Морозова", "Сергей Новиков", "Ольга Федорова",
    "Андрей Михайлов", "Татьяна Попова", "Павел Васильев", "Наталья Зайцева",
    "Максим Павлов", "Юлия Семенова", "Роман Голубев", "Екатерина Виноградова",
    "Владимир Лебедев", "Светлана Егорова", "Николай Романов", "Виктория Кузнецова"
]


def signal_handler(sig, frame):
    """Handle CTRL+C gracefully."""
    global running
    print("\n\n🛑 Stopping Telegram bot simulator...")
    running = False


def generate_telegram_contact() -> dict:
    """
    Generate new Telegram contact data.
    
    Returns:
        Contact data dictionary
    """
    if CONTACT_NAMES:
        name = CONTACT_NAMES.pop(0)
    else:
        name = f"Пользователь{random.randint(1000, 9999)}"
    
    # Generate username from name
    username = "@" + name.lower().replace(" ", "_").replace("а", "a").replace("е", "e")
    
    # Generate unique Telegram ID
    telegram_id = str(random.randint(100000000, 999999999))
    
    # Random first contact date (within last 30 days)
    days_ago = random.randint(1, 30)
    first_contact_date = datetime.now() - timedelta(days=days_ago)
    
    return {
        "name": name,
        "username": username,
        "telegram_id": telegram_id,
        "first_contact_date": first_contact_date,
        "chat_link": f"https://t.me/{username.lstrip('@')}"
    }


def create_contact_in_kommo(
    kommo_client: KommoClient,
    contact_data: dict,
    logger
) -> Optional[int]:
    """
    Create contact in Kommo with full metadata.
    
    Args:
        kommo_client: Kommo client instance
        contact_data: Contact data dictionary
        logger: Logger instance
        
    Returns:
        Contact ID if created, None if failed
    """
    try:
        # Get custom field IDs
        telegram_id_field = kommo_client.get_custom_field_by_name("Telegram ID")
        username_field = kommo_client.get_custom_field_by_name("Telegram Username")
        date_field = kommo_client.get_custom_field_by_name("First Contact Date")
        link_field = kommo_client.get_custom_field_by_name("Chat Link")
        
        # Build custom fields
        custom_fields = {}
        
        if telegram_id_field:
            custom_fields[telegram_id_field] = contact_data["telegram_id"]
        if username_field:
            custom_fields[username_field] = contact_data["username"]
        if date_field:
            # Format date as Unix timestamp for Kommo
            custom_fields[date_field] = int(contact_data["first_contact_date"].timestamp())
        if link_field:
            custom_fields[link_field] = contact_data["chat_link"]
        
        # Create contact
        contact_id = kommo_client.create_contact(
            name=contact_data["name"],
            custom_fields=custom_fields
        )
        
        logger.info(f"✅ Created contact: {contact_data['name']} (ID: {contact_id})")
        
        return contact_id
        
    except Exception as e:
        logger.error(f"Failed to create contact: {str(e)}")
        return None


def add_conversation_to_contact(
    kommo_client: KommoClient,
    message_simulator: MessageSimulator,
    contact_id: int,
    contact_name: str,
    username: str,
    logger
) -> Tuple[int, List[str]]:
    """
    Add simulated conversation to contact timeline.
    
    Args:
        kommo_client: Kommo client instance
        message_simulator: Message simulator instance
        contact_id: Contact ID
        contact_name: Contact name
        username: Telegram username
        logger: Logger instance
        
    Returns:
        Tuple of (messages_added, tags)
    """
    try:
        # Generate conversation
        conversation_type = random.choice(["support", "sales", "docs", "refund", "billing"])
        
        conversation = message_simulator.generate_conversation(
            contact_name=contact_name,
            telegram_username=username,
            conversation_type=conversation_type,
            num_exchanges=random.randint(2, 4)
        )
        
        # Add messages to timeline
        messages_added = 0
        
        for message in conversation:
            try:
                direction = "👤 Клиент" if message.is_incoming else "👨‍💼 Поддержка"
                timestamp_str = message.timestamp.strftime("%Y-%m-%d %H:%M")
                
                note_text = f"{direction} ({timestamp_str}):\n{message.text}"
                
                kommo_client.add_note_to_contact(
                    contact_id=contact_id,
                    note_text=note_text
                )
                
                messages_added += 1
                
            except Exception as e:
                logger.warning(f"Failed to add message: {str(e)}")
                continue
        
        # Extract unique tags
        tag_names = list(set(tag.value for msg in conversation for tag in msg.tags))
        
        # Add tags to contact
        if tag_names:
            try:
                kommo_client.add_tags_to_contact(contact_id, tag_names)
            except Exception as e:
                logger.warning(f"Failed to add tags: {str(e)}")
        
        logger.info(f"💬 Added {messages_added} messages, tags: {', '.join(tag_names)}")
        
        return messages_added, tag_names
        
    except Exception as e:
        logger.error(f"Failed to add conversation: {str(e)}")
        return 0, []


def simulate_telegram_activity(
    kommo_client: KommoClient,
    message_simulator: MessageSimulator,
    logger,
    new_contact_chance: float = 0.3
) -> dict:
    """
    Simulate single activity cycle (new contact or message to existing).
    
    Args:
        kommo_client: Kommo client instance
        message_simulator: Message simulator instance
        logger: Logger instance
        new_contact_chance: Probability of creating new contact vs messaging existing
        
    Returns:
        Activity statistics
    """
    stats = {
        "new_contact": False,
        "messages_added": 0,
        "contact_name": None,
        "tags": []
    }
    
    # Decide: new contact or message to existing?
    create_new = random.random() < new_contact_chance or len(ACTIVE_CONTACTS) == 0
    
    if create_new and len(ACTIVE_CONTACTS) < 50:
        # Create new contact
        contact_data = generate_telegram_contact()
        
        contact_id = create_contact_in_kommo(
            kommo_client=kommo_client,
            contact_data=contact_data,
            logger=logger
        )
        
        if contact_id:
            # Add initial conversation
            messages, tags = add_conversation_to_contact(
                kommo_client=kommo_client,
                message_simulator=message_simulator,
                contact_id=contact_id,
                contact_name=contact_data["name"],
                username=contact_data["username"],
                logger=logger
            )
            
            # Save to active contacts
            ACTIVE_CONTACTS.append({
                "id": contact_id,
                "name": contact_data["name"],
                "username": contact_data["username"]
            })
            
            stats["new_contact"] = True
            stats["messages_added"] = messages
            stats["contact_name"] = contact_data["name"]
            stats["tags"] = tags
    
    else:
        # Add message to existing contact
        if ACTIVE_CONTACTS:
            contact = random.choice(ACTIVE_CONTACTS)
            
            messages, tags = add_conversation_to_contact(
                kommo_client=kommo_client,
                message_simulator=message_simulator,
                contact_id=contact["id"],
                contact_name=contact["name"],
                username=contact["username"],
                logger=logger
            )
            
            stats["messages_added"] = messages
            stats["contact_name"] = contact["name"]
            stats["tags"] = tags
    
    return stats


def run_telegram_bot_simulator(
    kommo_client: KommoClient,
    message_simulator: MessageSimulator,
    logger,
    interval_range: tuple = (2, 10),
    new_contact_chance: float = 0.3
):
    """
    Main simulation loop.
    
    Args:
        kommo_client: Kommo client instance
        message_simulator: Message simulator instance
        logger: Logger instance
        interval_range: (min, max) seconds between activities
        new_contact_chance: Probability of new contact vs existing message
    """
    global running
    
    print("=" * 60)
    print("🤖 Telegram Bot Simulator for Kommo CRM")
    print("=" * 60)
    print(f"Interval: {interval_range[0]}-{interval_range[1]} seconds (randomized)")
    print(f"New contact chance: {int(new_contact_chance * 100)}%")
    print("=" * 60)
    print("\n🚀 Starting simulator... (Press CTRL+C to stop)\n")
    
    cycle = 0
    total_contacts_created = 0
    total_messages_added = 0
    
    try:
        while running:
            cycle += 1
            
            # Simulate activity
            stats = simulate_telegram_activity(
                kommo_client=kommo_client,
                message_simulator=message_simulator,
                logger=logger,
                new_contact_chance=new_contact_chance
            )
            
            # Update totals
            if stats["new_contact"]:
                total_contacts_created += 1
            
            total_messages_added += stats["messages_added"]
            
            # Display status
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if stats["new_contact"]:
                print(f"[{timestamp}] 🆕 New contact: {stats['contact_name']}")
            else:
                print(f"[{timestamp}] 💬 Message to: {stats['contact_name']}")
            
            print(f"   Contacts: {len(ACTIVE_CONTACTS)} | Messages: +{stats['messages_added']} | Total: {total_messages_added}")
            
            # Wait random interval
            if running:
                wait_time = random.randint(interval_range[0], interval_range[1])
                print(f"   ⏱️  Next activity in {wait_time} seconds...\n")
                time.sleep(wait_time)
        
        # Graceful shutdown
        print("\n" + "=" * 60)
        print("✓ Simulator stopped gracefully")
        print(f"Total cycles: {cycle}")
        print(f"Contacts created: {total_contacts_created}")
        print(f"Total messages: {total_messages_added}")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """CLI for Telegram bot simulator."""
    global running
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load configuration
        config = Config.from_env()
        logger = setup_logger_from_config(__name__, config)
        
        logger.info("✓ Configuration loaded")
        
        # Initialize Kommo client
        logger.info(f"Connecting to Kommo CRM (subdomain: {config.kommo_subdomain})...")
        
        kommo_client = KommoClient(
            subdomain=config.kommo_subdomain,
            access_token=config.kommo_access_token,
            logger=logger
        )
        
        # Test connection
        account_info = kommo_client.get_account_info()
        logger.info(f"✓ Connected to Kommo: {account_info.get('name')}")
        
        # Initialize message simulator
        message_simulator = MessageSimulator(logger)
        
        # Run simulator
        run_telegram_bot_simulator(
            kommo_client=kommo_client,
            message_simulator=message_simulator,
            logger=logger,
            interval_range=(2, 10),
            new_contact_chance=0.3
        )
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
