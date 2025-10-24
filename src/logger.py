"""
Logging module for Kommo CRM - Google Sheets Integration.
Configures colorful console output and rotating file logging.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional
import colorlog


def setup_logger(
    name: str,
    log_level: str = 'INFO',
    log_file_path: Optional[str] = None,
    log_max_bytes: int = 10485760,  # 10MB
    log_backup_count: int = 5
) -> logging.Logger:
    """
    Configure and return logger with console and file handlers.
    
    Args:
        name: Logger name (usually __name__ of the module)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file_path: Path to log file. If None, no file logging
        log_max_bytes: Maximum log file size before rotation
        log_backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    console_formatter = colorlog.ColoredFormatter(
        fmt='%(log_color)s[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s%(reset)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        reset=True,
        style='%'
    )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (if log_file_path is provided)
    if log_file_path:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=log_max_bytes,
            backupCount=log_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        file_formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def setup_logger_from_config(name: str, config) -> logging.Logger:
    """
    Configure logger using Config object.
    
    Args:
        name: Logger name (usually __name__ of the module)
        config: Config instance with logging settings
        
    Returns:
        Configured logger instance
    """
    return setup_logger(
        name=name,
        log_level=config.log_level,
        log_file_path=config.log_file_path,
        log_max_bytes=config.log_max_bytes,
        log_backup_count=config.log_backup_count
    )
