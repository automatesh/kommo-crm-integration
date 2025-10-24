"""
Configuration module for Kommo CRM - Google Sheets Integration.
Loads and validates configuration from environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


@dataclass
class Config:
    """
    Application configuration loaded from environment variables.
    
    Attributes:
        google_credentials_path: Path to Google service account JSON file
        google_sheet_id: Google Sheets document ID
        google_sheet_name: Name of the worksheet/tab
        kommo_subdomain: Kommo account subdomain
        kommo_access_token: Long-lived API access token
        kommo_api_base_url: Kommo API base URL
        sync_interval_seconds: Sync interval in seconds
        retry_attempts: Number of retry attempts for failed requests
        retry_delay_seconds: Delay between retries in seconds
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file_path: Path to log file
        log_max_bytes: Maximum log file size before rotation
        log_backup_count: Number of backup log files to keep
    """
    
    # Google Sheets
    google_credentials_path: str
    google_sheet_id: str
    google_sheet_name: str
    
    # Kommo CRM
    kommo_subdomain: str
    kommo_access_token: str
    kommo_api_base_url: str
    
    # Sync settings
    sync_interval_seconds: int
    retry_attempts: int
    retry_delay_seconds: int
    
    # Logging
    log_level: str
    log_file_path: str
    log_max_bytes: int
    log_backup_count: int
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> 'Config':
        """
        Load configuration from environment variables.
        
        Args:
            env_file: Optional path to .env file. If None, uses default .env
            
        Returns:
            Config instance with loaded values
            
        Raises:
            ConfigError: If required environment variables are missing or invalid
        """
        # Load .env file if it exists
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        try:
            # Google Sheets configuration
            google_credentials_path = os.getenv(
                'GOOGLE_CREDENTIALS_PATH',
                './credentials/google_service_account.json'
            )
            google_sheet_id = os.getenv('GOOGLE_SHEET_ID', '')
            google_sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Orders')
            
            # Kommo CRM configuration
            kommo_subdomain = os.getenv('KOMMO_SUBDOMAIN', '')
            kommo_access_token = os.getenv('KOMMO_ACCESS_TOKEN', '')
            
            # Sync settings
            sync_interval_seconds = int(os.getenv('SYNC_INTERVAL_SECONDS', '10'))
            retry_attempts = int(os.getenv('RETRY_ATTEMPTS', '3'))
            retry_delay_seconds = int(os.getenv('RETRY_DELAY_SECONDS', '5'))
            
            # Logging settings
            log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
            log_file_path = os.getenv('LOG_FILE_PATH', './logs/kommo-sync.log')
            log_max_bytes = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
            log_backup_count = int(os.getenv('LOG_BACKUP_COUNT', '5'))
            
            # Construct Kommo API base URL
            kommo_api_base_url = 'https://api-c.kommo.com'
            
            config = cls(
                google_credentials_path=google_credentials_path,
                google_sheet_id=google_sheet_id,
                google_sheet_name=google_sheet_name,
                kommo_subdomain=kommo_subdomain,
                kommo_access_token=kommo_access_token,
                kommo_api_base_url=kommo_api_base_url,
                sync_interval_seconds=sync_interval_seconds,
                retry_attempts=retry_attempts,
                retry_delay_seconds=retry_delay_seconds,
                log_level=log_level,
                log_file_path=log_file_path,
                log_max_bytes=log_max_bytes,
                log_backup_count=log_backup_count
            )
            
            # Validate configuration
            config.validate()
            
            return config
            
        except ValueError as e:
            raise ConfigError(f"Invalid configuration value: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")
    
    def validate(self) -> bool:
        """
        Validate that all required configuration is present and valid.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigError: If configuration is invalid
        """
        errors = []
        
        # Validate Google Sheets settings
        if not self.google_sheet_id:
            errors.append("GOOGLE_SHEET_ID is required")
        
        if not os.path.exists(self.google_credentials_path):
            errors.append(
                f"Google credentials file not found: {self.google_credentials_path}"
            )
        
        # Validate Kommo settings
        if not self.kommo_subdomain:
            errors.append("KOMMO_SUBDOMAIN is required")
        
        if not self.kommo_access_token:
            errors.append("KOMMO_ACCESS_TOKEN is required")
        
        # Validate sync settings
        if self.sync_interval_seconds < 1:
            errors.append("SYNC_INTERVAL_SECONDS must be >= 1")
        
        if self.retry_attempts < 0:
            errors.append("RETRY_ATTEMPTS must be >= 0")
        
        if self.retry_delay_seconds < 0:
            errors.append("RETRY_DELAY_SECONDS must be >= 0")
        
        # Validate logging settings
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_log_levels:
            errors.append(
                f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}"
            )
        
        if self.log_max_bytes < 1024:
            errors.append("LOG_MAX_BYTES must be >= 1024")
        
        if self.log_backup_count < 0:
            errors.append("LOG_BACKUP_COUNT must be >= 0")
        
        # Raise error if any validation failed
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            raise ConfigError(error_message)
        
        return True
    
    def get_kommo_base_url(self) -> str:
        """
        Get the Kommo account base URL.
        
        Returns:
            Base URL for the Kommo account (e.g., https://subdomain.kommo.com)
        """
        return f"https://{self.kommo_subdomain}.kommo.com"
    
    def __repr__(self) -> str:
        """
        String representation of config (without sensitive data).
        
        Returns:
            Safe string representation
        """
        return (
            f"Config("
            f"subdomain={self.kommo_subdomain}, "
            f"sheet_id={self.google_sheet_id[:8]}..., "
            f"sync_interval={self.sync_interval_seconds}s, "
            f"log_level={self.log_level}"
            f")"
        )
