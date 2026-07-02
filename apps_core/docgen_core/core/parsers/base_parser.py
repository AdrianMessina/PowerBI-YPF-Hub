"""
Abstract base parser for Power BI files
Defines the interface that all parsers must implement
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
import logging

from ..models import ReportMetadata


class BasePowerBIParser(ABC):
    """
    Abstract base class for Power BI parsers
    All concrete parsers (PBIP, PBIX) must implement this interface
    """

    def __init__(self, file_path: Union[str, Path]):
        """
        Initialize the parser

        Args:
            file_path: Path to the Power BI file or project
        """
        self.file_path = Path(file_path) if isinstance(file_path, str) else file_path
        self.logger = logging.getLogger(self.__class__.__name__)

        # Validate file exists
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

    @abstractmethod
    def parse(self) -> ReportMetadata:
        """
        Parse the Power BI file and extract all metadata

        Returns:
            ReportMetadata: Complete metadata structure

        Raises:
            Exception: If parsing fails
        """
        pass

    @abstractmethod
    def supports_format(self) -> bool:
        """
        Check if this parser supports the given file format

        Returns:
            bool: True if parser can handle this file
        """
        pass

    @abstractmethod
    def validate_file(self) -> bool:
        """
        Validate that the file is in the correct format

        Returns:
            bool: True if file is valid for this parser

        Raises:
            ValueError: If file is invalid with details
        """
        pass

    def get_report_name(self) -> str:
        """
        Get the report name from the file path

        Returns:
            str: Report name
        """
        return self.file_path.stem

    def _log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)
        print(f"ℹ️  {message}")

    def _log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
        print(f"⚠️  {message}")

    def _log_error(self, message: str):
        """Log error message"""
        self.logger.error(message)
        print(f"❌ {message}")

    def _log_success(self, message: str):
        """Log success message"""
        self.logger.info(message)
        print(f"✅ {message}")
