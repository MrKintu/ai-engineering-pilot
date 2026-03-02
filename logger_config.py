"""Centralized logging configuration for the AI Engineering Fellowship project."""

import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """Set up a logger with file and console handlers.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Optional custom log file name. If None, uses name-based naming.
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid adding handlers if they already exist
    if logger.handlers:
        return logger
    
    # Determine log file path
    if log_file is None:
        # Use module name for log file
        safe_name = name.replace("__main__", "main").replace(".", "_")
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = f"{safe_name}_{timestamp}.log"
    
    log_path = logs_dir / log_file
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Convenience function for getting a logger
def get_logger(name: str) -> logging.Logger:
    """Get a logger with standard configuration."""
    return setup_logger(name)
