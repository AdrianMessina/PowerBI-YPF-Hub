"""
Auto-detection of Power BI file format (PBIX vs PBIP)
"""

import os
import zipfile
from pathlib import Path
from typing import Union, Optional, Tuple
from enum import Enum


class PowerBIFormat(Enum):
    """Power BI file formats"""
    PBIX = "pbix"  # Legacy format (ZIP with JSON/binary)
    PBIP = "pbip"  # Modern format (folder structure with TMDL/JSON)
    UNKNOWN = "unknown"


class FormatDetector:
    """
    Detects the format of a Power BI file or project
    """

    @staticmethod
    def detect(path: Union[str, Path]) -> PowerBIFormat:
        """
        Detect the format of a Power BI file or project

        Args:
            path: Path to file or directory

        Returns:
            PowerBIFormat: Detected format

        Examples:
            >>> FormatDetector.detect("report.pbix")
            PowerBIFormat.PBIX

            >>> FormatDetector.detect("MyProject.pbip")
            PowerBIFormat.PBIP

            >>> FormatDetector.detect("MyProject.Report")
            PowerBIFormat.PBIP
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        # Check if it's a .pbix file
        if path.is_file() and path.suffix.lower() == '.pbix':
            if FormatDetector._validate_pbix(path):
                return PowerBIFormat.PBIX
            return PowerBIFormat.UNKNOWN

        # Check if it's a .pbip file (project file)
        if path.is_file() and path.suffix.lower() == '.pbip':
            return PowerBIFormat.PBIP

        # Check if it's a PBIP directory (.Report or .SemanticModel)
        if path.is_dir():
            if FormatDetector._is_pbip_directory(path):
                return PowerBIFormat.PBIP

        return PowerBIFormat.UNKNOWN

    @staticmethod
    def _validate_pbix(path: Path) -> bool:
        """
        Validate that a .pbix file is actually a valid ZIP file

        Args:
            path: Path to .pbix file

        Returns:
            bool: True if valid PBIX
        """
        try:
            with zipfile.ZipFile(path, 'r') as zip_ref:
                # Check for expected files in PBIX
                expected_files = ['DataModel', 'Report/Layout']
                file_list = zip_ref.namelist()

                # At least one of the expected files should exist
                return any(expected in file_list for expected in expected_files)
        except (zipfile.BadZipFile, Exception):
            return False

    @staticmethod
    def _is_pbip_directory(path: Path) -> bool:
        """
        Check if directory is a PBIP project directory

        Args:
            path: Path to directory

        Returns:
            bool: True if PBIP directory
        """
        path_name = path.name

        # Check if it's a .Report or .SemanticModel/.Dataset folder
        if path_name.endswith('.Report') or \
           path_name.endswith('.SemanticModel') or \
           path_name.endswith('.Dataset'):
            return True

        # Check if directory contains PBIP project structure
        # Look for .pbip file or Report/SemanticModel folders
        for item in path.iterdir():
            if item.is_file() and item.suffix.lower() == '.pbip':
                return True
            if item.is_dir() and (
                item.name.endswith('.Report') or
                item.name.endswith('.SemanticModel') or
                item.name.endswith('.Dataset')
            ):
                return True

        return False

    @staticmethod
    def resolve_pbip_paths(pbip_path: Union[str, Path]) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Resolve PBIP project to Report and SemanticModel paths

        Args:
            pbip_path: Path to .pbip file or project directory

        Returns:
            Tuple of (report_path, semantic_model_path)
            Either can be None if not found

        Examples:
            >>> report, model = FormatDetector.resolve_pbip_paths("MyProject.pbip")
            >>> print(report)  # MyProject.Report
            >>> print(model)   # MyProject.SemanticModel
        """
        pbip_path = Path(pbip_path)

        # If it's a .pbip file, look for sibling folders
        if pbip_path.is_file() and pbip_path.suffix.lower() == '.pbip':
            base_name = pbip_path.stem
            parent_dir = pbip_path.parent

            report_path = parent_dir / f"{base_name}.Report"
            semantic_path = parent_dir / f"{base_name}.SemanticModel"
            dataset_path = parent_dir / f"{base_name}.Dataset"  # Legacy name

            report_path = report_path if report_path.exists() else None
            semantic_path = semantic_path if semantic_path.exists() else (
                dataset_path if dataset_path.exists() else None
            )

            return report_path, semantic_path

        # If it's a directory ending with .Report
        if pbip_path.is_dir() and pbip_path.name.endswith('.Report'):
            base_name = pbip_path.name.replace('.Report', '')
            parent_dir = pbip_path.parent

            semantic_path = parent_dir / f"{base_name}.SemanticModel"
            dataset_path = parent_dir / f"{base_name}.Dataset"

            semantic_path = semantic_path if semantic_path.exists() else (
                dataset_path if dataset_path.exists() else None
            )

            return pbip_path, semantic_path

        # If it's a directory ending with .SemanticModel or .Dataset
        if pbip_path.is_dir() and (
            pbip_path.name.endswith('.SemanticModel') or
            pbip_path.name.endswith('.Dataset')
        ):
            base_name = pbip_path.name.replace('.SemanticModel', '').replace('.Dataset', '')
            parent_dir = pbip_path.parent

            report_path = parent_dir / f"{base_name}.Report"
            report_path = report_path if report_path.exists() else None

            return report_path, pbip_path

        # If it's a generic directory, search for .Report and .SemanticModel subdirectories
        if pbip_path.is_dir():
            report_path = None
            semantic_path = None

            for item in pbip_path.iterdir():
                if item.is_dir():
                    if item.name.endswith('.Report'):
                        report_path = item
                    elif item.name.endswith('.SemanticModel') or item.name.endswith('.Dataset'):
                        semantic_path = item

            return report_path, semantic_path

        return None, None


def detect_and_log(path: Union[str, Path]) -> PowerBIFormat:
    """
    Detect format and print information

    Args:
        path: Path to Power BI file or project

    Returns:
        PowerBIFormat: Detected format
    """
    format_type = FormatDetector.detect(path)

    print(f"📂 Analyzing: {path}")
    print(f"🔍 Detected format: {format_type.value.upper()}")

    if format_type == PowerBIFormat.PBIP:
        report_path, model_path = FormatDetector.resolve_pbip_paths(path)
        if report_path:
            print(f"   📄 Report: {report_path}")
        if model_path:
            print(f"   📊 Model: {model_path}")

    return format_type
