"""
Parsers for Power BI files
"""

from .base_parser import BasePowerBIParser
from .pbip_parser import PBIPParser
from .pbix_parser import PBIXParser
from .format_detector import FormatDetector, PowerBIFormat, detect_and_log
from .tmdl_reader import TMDLReader


def create_parser(file_path: str):
    """
    Factory function to create appropriate parser based on file format
    """
    format_type = FormatDetector.detect(file_path)

    if format_type == PowerBIFormat.PBIP:
        return PBIPParser(file_path)
    elif format_type == PowerBIFormat.PBIX:
        return PBIXParser(file_path)
    else:
        raise ValueError(f"Unsupported format: {format_type}")


__all__ = [
    "BasePowerBIParser",
    "PBIPParser",
    "PBIXParser",
    "FormatDetector",
    "PowerBIFormat",
    "TMDLReader",
    "create_parser",
    "detect_and_log"
]

