"""
Kommo CRM API client for integration.
Handles authentication, contact search, and note management.
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from retrying import retry


class KommoAPIError(Exception):
    """Base exception for Kommo API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data
        self.message = message


class KommoAuthError(KommoAPIError):
    """Authentication/authorization errors (401, 403)."""
    pass


class KommoRateLimitError(KommoAPIError):
    """Rate limiting errors (429)."""
    
    def __init__(self, message: str, retry_after: int = 60, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


@dataclass
class KommoContact:
    """
    Kommo contact data model.
    
    Attributes:
        id: Contact ID in Kommo
        name: Contact name
        telegram_id: Telegram ID from custom field
        custom_fields: Dictionary of custom fields
    """
    id: int
    name: str
    telegram_id: Optional[str]
    custom_fields: Dict[str, Any]
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'KommoContact':
        """
        Parse API response into Contact object.
        
        Args:
            data: Contact data from Kommo API
            
        Returns:
            KommoContact instance
        """
        contact_id = data.get('id')
        name = data.get('name', 'Unknown')
        
        # Extract custom fields
        custom_fields = {}
        telegram_id = None
        
        if 'custom_fields_values' in data:
            for field in data['custom_fields_values']:
                field_name = field.get('field_name', '')
                field_values = field.get('values', [])
                
                if field_values:
                    field_value = field_values[0].get('value')
                    custom_fields[field_name] = field_value
                    
                    # Check if this is the Telegram ID field
                    if field_name.lower() in ['telegram id', 'telegram_id', 'telegram']:
                        telegram_id = str(field_value) if field_value else None
        
        return cls(
            id=contact_id,
            name=name,
            telegram_id=telegram_id,
            custom_fields=custom_fields
        )


@dataclass
class KommoNote:
    """
    Kommo note data model.
    
    Attributes:
        note_type: Type of note (e.g., "common")
        params: Note parameters including text
        created_at: Creation timestamp
    """
    note_type: str
    params: Dict[str, Any]
    created_at: int
    
    def matches_order(self, order) -> bool:
        """
        Check if note corresponds to this order.
        
        Args:
            order: Order object to compare
            
        Returns:
            True if note matches order
        """
        # Extract note text
        note_text = self.params.get('text', '')
        
        # Simple matching based on product name and amount
        return (
            str(order.product) in note_text and
            str(order.amount) in note_text
        )


class KommoClient:
    """
    Main API client for Kommo CRM.
    
    Attributes:
        subdomain: Kommo account subdomain
        access_token: Long-lived API access token
        base_url: Account base URL
        api_url: API base URL
        logger: Logger instance
        session: Requests session with retry logic
    """
    
    def __init__(
        self,
        subdomain: str,
        access_token: str,
        logger: logging.Logger,
        retry_attempts: int = 3,
        retry_delay: int = 5
    ):
        """
        Initialize Kommo API client.
        
        Args:
            subdomain: Kommo account subdomain
            access_token: Long-lived API access token
            logger: Logger instance
            retry_attempts: Number of retry attempts for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.subdomain = subdomain
        self.access_token = access_token
        self.base_url = f"https://{subdomain}.kommo.com"
        self.api_url = f"https://{subdomain}.kommo.com"  # Use subdomain URL instead of api-c
        self.logger = logger
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Create session with retry logic
        self.session = self._create_session()
        
        self.logger.info(f"Initialized Kommo client for subdomain: {subdomain}")
    
    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry logic.
        
        Returns:
            Configured session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retry_attempts,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Internal method for making HTTP requests to Kommo API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/v4/contacts")
            data: Request body data (for POST/PUT)
            params: Query parameters
            max_retries: Override retry attempts
            
        Returns:
            Response JSON data
            
        Raises:
            KommoAuthError: Authentication failed
            KommoRateLimitError: Rate limit exceeded
            KommoAPIError: Other API errors
        """
        url = f"{self.api_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        retries = max_retries if max_retries is not None else self.retry_attempts
        last_exception = None
        
        for attempt in range(retries + 1):
            try:
                self.logger.debug(f"{method} {endpoint} (attempt {attempt + 1}/{retries + 1})")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=30
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.logger.warning(f"Rate limit exceeded. Retry after {retry_after} seconds")
                    
                    if attempt < retries:
                        time.sleep(retry_after)
                        continue
                    else:
                        raise KommoRateLimitError(
                            f"Rate limit exceeded",
                            retry_after=retry_after,
                            status_code=response.status_code
                        )
                
                # Handle authentication errors
                if response.status_code in [401, 403]:
                    error_msg = f"Authentication failed: {response.status_code} - {response.text}"
                    self.logger.error(error_msg)
                    raise KommoAuthError(
                        error_msg,
                        status_code=response.status_code,
                        response_data=response.json() if response.text else None
                    )
                
                # Handle other client/server errors
                if response.status_code >= 400:
                    error_msg = f"API request failed: {response.status_code} - {response.text}"
                    self.logger.error(error_msg)
                    
                    if attempt < retries:
                        self.logger.info(f"Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                        continue
                    
                    raise KommoAPIError(
                        error_msg,
                        status_code=response.status_code,
                        response_data=response.json() if response.text else None
                    )
                
                # Success
                self.logger.debug(f"Request successful: {response.status_code}")
                
                # Return JSON response or empty dict
                try:
                    return response.json() if response.text else {}
                except ValueError:
                    return {}
                    
            except (requests.RequestException, ConnectionError) as e:
                last_exception = e
                self.logger.warning(f"Request failed: {str(e)}")
                
                if attempt < retries:
                    self.logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    error_msg = f"Request failed after {retries + 1} attempts: {str(e)}"
                    self.logger.error(error_msg)
                    raise KommoAPIError(error_msg) from e
        
        # Should not reach here, but just in case
        raise KommoAPIError(f"Request failed: {str(last_exception)}")
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Test API connection and get account information.
        
        Returns:
            Account details
            
        Raises:
            KommoAPIError: If request fails
        """
        self.logger.info("Fetching account information")
        
        try:
            response = self._make_request('GET', '/api/v4/account')
            
            account_name = response.get('name', 'Unknown')
            account_id = response.get('id', 'Unknown')
            
            self.logger.info(f"Connected to account: {account_name} (ID: {account_id})")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to get account info: {str(e)}")
            raise
    
    def find_contact_by_telegram_id(self, telegram_id: str) -> Optional[KommoContact]:
        """
        Search for contact by custom field "Telegram ID".
        
        Args:
            telegram_id: Telegram ID to search for
            
        Returns:
            KommoContact if found, None otherwise
            
        Raises:
            KommoAPIError: If search fails
        """
        self.logger.debug(f"Searching for contact with Telegram ID: {telegram_id}")
        
        try:
            # Search contacts with query parameter
            params = {
                'query': telegram_id
            }
            
            response = self._make_request('GET', '/api/v4/contacts', params=params)
            
            # Check if contacts were found
            embedded = response.get('_embedded', {})
            contacts = embedded.get('contacts', [])
            
            if not contacts:
                self.logger.info(f"No contact found for Telegram ID: {telegram_id}")
                return None
            
            # Filter contacts that actually match the Telegram ID
            matching_contacts = []
            for contact_data in contacts:
                contact = KommoContact.from_api_response(contact_data)
                
                # Check if Telegram ID matches
                if contact.telegram_id and contact.telegram_id == telegram_id:
                    matching_contacts.append(contact)
            
            if not matching_contacts:
                self.logger.info(f"No exact match found for Telegram ID: {telegram_id}")
                return None
            
            # Handle multiple matches (log warning, return first)
            if len(matching_contacts) > 1:
                self.logger.warning(
                    f"Found {len(matching_contacts)} contacts with Telegram ID {telegram_id}. "
                    f"Using first match: {matching_contacts[0].name}"
                )
            
            contact = matching_contacts[0]
            self.logger.info(f"Found contact: {contact.name} (ID: {contact.id})")
            
            return contact
            
        except Exception as e:
            self.logger.error(f"Failed to search contact: {str(e)}")
            raise
    
    def get_contact_notes(self, contact_id: int) -> List[KommoNote]:
        """
        Retrieve all notes for a specific contact.
        
        Args:
            contact_id: Contact ID
            
        Returns:
            List of KommoNote objects
            
        Raises:
            KommoAPIError: If request fails
        """
        self.logger.debug(f"Fetching notes for contact ID: {contact_id}")
        
        try:
            response = self._make_request('GET', f'/api/v4/contacts/{contact_id}/notes')
            
            # Extract notes from response
            embedded = response.get('_embedded', {})
            notes_data = embedded.get('notes', [])
            
            notes = []
            for note_data in notes_data:
                note = KommoNote(
                    note_type=note_data.get('note_type', ''),
                    params=note_data.get('params', {}),
                    created_at=note_data.get('created_at', 0)
                )
                notes.append(note)
            
            self.logger.info(f"Found {len(notes)} notes for contact {contact_id}")
            
            return notes
            
        except Exception as e:
            self.logger.error(f"Failed to get contact notes: {str(e)}")
            raise
    
    def add_note_to_contact(
        self,
        contact_id: int,
        note_text: str,
        note_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a new note to contact timeline.
        
        Args:
            contact_id: Contact ID
            note_text: Note text content
            note_title: Optional note title (not used by Kommo API, kept for compatibility)
            
        Returns:
            Created note data from API
            
        Raises:
            KommoAPIError: If request fails
        """
        self.logger.debug(f"Adding note to contact {contact_id}")
        
        try:
            # Prepare note payload
            payload = [
                {
                    "note_type": "common",
                    "params": {
                        "text": note_text
                    }
                }
            ]
            
            response = self._make_request(
                'POST',
                f'/api/v4/contacts/{contact_id}/notes',
                data=payload
            )
            
            self.logger.info(f"Successfully added note to contact {contact_id}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to add note: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test API connection.
        
        Returns:
            True if connection is successful
        """
        try:
            self.get_account_info()
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_custom_fields(self) -> List[Dict[str, Any]]:
        """
        Get all custom fields from account.
        
        Returns:
            List of custom field definitions
            
        Raises:
            KommoAPIError: If request fails
        """
        self.logger.debug("Fetching custom fields")
        
        try:
            response = self._make_request('GET', '/api/v4/contacts/custom_fields')
            
            # Extract custom fields from response
            embedded = response.get('_embedded', {})
            custom_fields = embedded.get('custom_fields', [])
            
            self.logger.info(f"Found {len(custom_fields)} custom fields")
            
            return custom_fields
            
        except Exception as e:
            self.logger.error(f"Failed to get custom fields: {str(e)}")
            raise
    
    def create_custom_field(self, field_name: str, field_type: str = "text") -> int:
        """
        Create new custom field in contacts.
        
        Args:
            field_name: Name of the custom field
            field_type: Type of field (text, numeric, checkbox, etc.)
            
        Returns:
            Custom field ID
            
        Raises:
            KommoAPIError: If request fails
        """
        self.logger.info(f"Creating custom field: {field_name}")
        
        try:
            payload = [
                {
                    "name": field_name,
                    "type": field_type
                }
            ]
            
            response = self._make_request(
                'POST',
                '/api/v4/contacts/custom_fields',
                data=payload
            )
            
            # Extract field ID from response
            embedded = response.get('_embedded', {})
            custom_fields = embedded.get('custom_fields', [])
            
            if custom_fields:
                field_id = custom_fields[0].get('id')
                self.logger.info(f"Created custom field '{field_name}' with ID: {field_id}")
                return field_id
            else:
                raise KommoAPIError("Failed to get field ID from response")
            
        except Exception as e:
            self.logger.error(f"Failed to create custom field: {str(e)}")
            raise
    
    def create_contact(
        self,
        name: str,
        custom_fields: Optional[Dict[int, Any]] = None,
        **kwargs
    ) -> int:
        """
        Create new contact in Kommo.
        
        Args:
            name: Contact name
            custom_fields: Dictionary of {field_id: value}
            **kwargs: Additional contact fields (email, phone, etc.)
            
        Returns:
            Created contact ID
            
        Raises:
            KommoAPIError: If request fails
        """
        self.logger.info(f"Creating contact: {name}")
        
        try:
            # Build contact payload
            contact_data = {
                "name": name
            }
            
            # Add custom fields if provided
            if custom_fields:
                custom_fields_values = []
                for field_id, value in custom_fields.items():
                    custom_fields_values.append({
                        "field_id": field_id,
                        "values": [{"value": value}]
                    })
                contact_data["custom_fields_values"] = custom_fields_values
            
            # Add any additional fields
            if kwargs:
                contact_data.update(kwargs)
            
            payload = [contact_data]
            
            response = self._make_request(
                'POST',
                '/api/v4/contacts',
                data=payload
            )
            
            # Extract contact ID from response
            embedded = response.get('_embedded', {})
            contacts = embedded.get('contacts', [])
            
            if contacts:
                contact_id = contacts[0].get('id')
                self.logger.info(f"Created contact '{name}' with ID: {contact_id}")
                return contact_id
            else:
                raise KommoAPIError("Failed to get contact ID from response")
            
        except Exception as e:
            self.logger.error(f"Failed to create contact: {str(e)}")
            raise
    
    def update_contact(
        self,
        contact_id: int,
        name: Optional[str] = None,
        custom_fields: Optional[Dict[int, Any]] = None,
        **kwargs
    ) -> bool:
        """
        Update existing contact fields.
        
        Args:
            contact_id: Contact ID to update
            name: New contact name (optional)
            custom_fields: Dictionary of {field_id: value}
            **kwargs: Additional fields to update
            
        Returns:
            True if successful
            
        Raises:
            KommoAPIError: If update fails
        """
        self.logger.info(f"Updating contact ID: {contact_id}")
        
        try:
            # Build update payload
            contact_data = {}
            
            if name:
                contact_data["name"] = name
            
            # Add custom fields if provided
            if custom_fields:
                custom_fields_values = []
                for field_id, value in custom_fields.items():
                    custom_fields_values.append({
                        "field_id": field_id,
                        "values": [{"value": value}]
                    })
                contact_data["custom_fields_values"] = custom_fields_values
            
            # Add any additional fields
            if kwargs:
                contact_data.update(kwargs)
            
            if not contact_data:
                self.logger.warning("No fields to update")
                return True
            
            response = self._make_request(
                'PATCH',
                f'/api/v4/contacts/{contact_id}',
                data=contact_data
            )
            
            self.logger.info(f"Successfully updated contact {contact_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update contact: {str(e)}")
            raise
    
    def get_custom_field_by_name(self, field_name: str) -> Optional[int]:
        """
        Find custom field ID by name.
        
        Args:
            field_name: Field name to search
            
        Returns:
            Field ID if found, None otherwise
        """
        self.logger.debug(f"Searching for custom field: {field_name}")
        
        try:
            custom_fields = self.get_custom_fields()
            
            # Case-insensitive search
            field_name_lower = field_name.lower()
            
            for field in custom_fields:
                if field.get('name', '').lower() == field_name_lower:
                    field_id = field.get('id')
                    self.logger.debug(f"Found field '{field_name}' with ID: {field_id}")
                    return field_id
            
            self.logger.debug(f"Custom field '{field_name}' not found")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to search custom field: {str(e)}")
            return None
    
    def get_or_create_tag(self, tag_name: str) -> int:
        """
        Get existing tag ID or create new one for contacts.
        
        Args:
            tag_name: Tag name
            
        Returns:
            Tag ID
            
        Raises:
            KommoAPIError: If operation fails
        """
        self.logger.debug(f"Getting or creating tag: {tag_name}")
        
        try:
            # Get all contact tags
            response = self._make_request('GET', '/api/v4/contacts/tags')
            
            # Search for existing tag
            embedded = response.get('_embedded', {})
            tags = embedded.get('tags', [])
            
            for tag in tags:
                if tag.get('name') == tag_name:
                    tag_id = tag.get('id')
                    self.logger.debug(f"Found existing tag '{tag_name}' with ID: {tag_id}")
                    return tag_id
            
            # Tag doesn't exist, create it
            self.logger.info(f"Creating new tag: {tag_name}")
            
            payload = [{"name": tag_name}]
            
            create_response = self._make_request(
                'POST',
                '/api/v4/contacts/tags',
                data=payload
            )
            
            created_embedded = create_response.get('_embedded', {})
            created_tags = created_embedded.get('tags', [])
            
            if created_tags:
                tag_id = created_tags[0].get('id')
                self.logger.info(f"Created tag '{tag_name}' with ID: {tag_id}")
                return tag_id
            else:
                raise KommoAPIError("Failed to get tag ID from response")
            
        except Exception as e:
            self.logger.error(f"Failed to get/create tag: {str(e)}")
            raise
    
    def add_tags_to_contact(
        self,
        contact_id: int,
        tags: List[str]
    ) -> bool:
        """
        Add tags to contact.
        
        Args:
            contact_id: Contact ID
            tags: List of tag names
            
        Returns:
            True if successful
            
        Raises:
            KommoAPIError: If operation fails
        """
        self.logger.info(f"Adding {len(tags)} tags to contact {contact_id}")
        
        try:
            # Get or create tag IDs
            tag_ids = []
            for tag_name in tags:
                tag_id = self.get_or_create_tag(tag_name)
                tag_ids.append({"id": tag_id})
            
            # Update contact with tags
            contact_data = {
                "_embedded": {
                    "tags": tag_ids
                }
            }
            
            self._make_request(
                'PATCH',
                f'/api/v4/contacts/{contact_id}',
                data=contact_data
            )
            
            self.logger.info(f"Successfully added tags to contact {contact_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add tags: {str(e)}")
            raise
    
    def create_lead(
        self,
        name: str,
        price: float,
        contact_id: Optional[int] = None,
        custom_fields: Optional[Dict[int, Any]] = None,
        **kwargs
    ) -> int:
        """
        Create new lead (deal) in Kommo.
        
        Args:
            name: Lead name (e.g., "Order #123" or product name)
            price: Lead price/budget
            contact_id: Associated contact ID (optional)
            custom_fields: Dictionary of {field_id: value}
            **kwargs: Additional lead fields
            
        Returns:
            Created lead ID
            
        Raises:
            KommoAPIError: If request fails
        """
        self.logger.info(f"Creating lead: {name} (price: {price})")
        
        try:
            # Build lead payload
            lead_data = {
                "name": name,
                "price": int(price)  # Kommo expects integer price in minor units
            }
            
            # Add contact if provided
            if contact_id:
                lead_data["_embedded"] = {
                    "contacts": [{"id": contact_id}]
                }
            
            # Add custom fields if provided
            if custom_fields:
                custom_fields_values = []
                for field_id, value in custom_fields.items():
                    custom_fields_values.append({
                        "field_id": field_id,
                        "values": [{"value": value}]
                    })
                lead_data["custom_fields_values"] = custom_fields_values
            
            # Add any additional fields
            if kwargs:
                lead_data.update(kwargs)
            
            payload = [lead_data]
            
            response = self._make_request(
                'POST',
                '/api/v4/leads',
                data=payload
            )
            
            # Extract lead ID from response
            embedded = response.get('_embedded', {})
            leads = embedded.get('leads', [])
            
            if leads:
                lead_id = leads[0].get('id')
                self.logger.info(f"Created lead '{name}' with ID: {lead_id}")
                return lead_id
            else:
                raise KommoAPIError("Failed to get lead ID from response")
            
        except Exception as e:
            self.logger.error(f"Failed to create lead: {str(e)}")
            raise
