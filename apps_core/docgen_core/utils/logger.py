"""
Logging configuration for the application
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import yaml


def setup_logging(
    config_path: Optional[Path] = None,
    log_level: str = "INFO",
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Setup application logging

    Args:
        config_path: Path to config file (optional)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)

    Returns:
        Logger instance
    """
    # Load config if provided
    if config_path and config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logging_config = config.get('logging', {})
            log_level = logging_config.get('level', log_level)
            log_format = logging_config.get(
                'format',
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            if not log_file:
                log_file_str = logging_config.get('file')
                if log_file_str:
                    log_file = Path(log_file_str)
    else:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
