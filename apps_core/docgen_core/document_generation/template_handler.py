"""
Word Template Handler

Manages YPF corporate template styles and formatting.
"""

from docx import Document
from docx.shared import Pt, RGBColor
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class TemplateHandler:
    """Handles Word template styles and corporate formatting"""

    def __init__(self, doc: Document):
        """
        Initialize template handler

        Args:
            doc: Document object
        """
        self.doc = doc
        self._available_styles = self._get_available_styles()

    def _get_available_styles(self) -> set:
        """
        Get available styles in the document

        Returns:
            Set of style names
        """
        try:
            return {style.name for style in self.doc.styles}
        except Exception as e:
            logger.warning(f"Could not retrieve styles: {e}")
            return set()

    def apply_corporate_style(self, paragraph: Any, style_name: str) -> None:
        """
        Apply YPF corporate style to paragraph

        Args:
            paragraph: Paragraph object
            style_name: Style name to apply
        """
        # Try to apply style if it exists in template
        if style_name in self._available_styles:
            try:
                paragraph.style = style_name
                return
            except Exception as e:
                logger.debug(f"Could not apply style {style_name}: {e}")

        # Fallback to manual formatting
        self._apply_manual_formatting(paragraph, style_name)

    def _apply_manual_formatting(self, paragraph: Any, style_type: str) -> None:
        """
        Apply manual formatting when template style is not available

        Args:
            paragraph: Paragraph object
            style_type: Type of formatting to apply
        """
        if style_type.startswith('Heading'):
            level = int(style_type.split()[-1]) if len(style_type.split()) > 1 else 1
            self._apply_heading_format(paragraph, level)
        elif style_type == 'Normal':
            self._apply_normal_format(paragraph)
        elif style_type == 'Code':
            self._apply_code_format(paragraph)
        elif style_type == 'Caption':
            self._apply_caption_format(paragraph)

    def _apply_heading_format(self, paragraph: Any, level: int) -> None:
        """Apply heading format"""
        for run in paragraph.runs:
            run.bold = True
            if level == 1:
                run.font.size = Pt(18)
                run.font.color.rgb = RGBColor(26, 54, 93)  # YPF Dark Blue
            elif level == 2:
                run.font.size = Pt(14)
                run.font.color.rgb = RGBColor(26, 54, 93)
            elif level == 3:
                run.font.size = Pt(12)
                run.font.color.rgb = RGBColor(26, 54, 93)
            else:
                run.font.size = Pt(11)
                run.font.color.rgb = RGBColor(51, 51, 51)

    def _apply_normal_format(self, paragraph: Any) -> None:
        """Apply normal text format"""
        for run in paragraph.runs:
            run.font.size = Pt(11)
            run.font.name = 'Calibri'
            run.font.color.rgb = RGBColor(51, 51, 51)

    def _apply_code_format(self, paragraph: Any) -> None:
        """Apply code format"""
        for run in paragraph.runs:
            run.font.size = Pt(9)
            run.font.name = 'Consolas'
            run.font.color.rgb = RGBColor(51, 51, 51)

    def _apply_caption_format(self, paragraph: Any) -> None:
        """Apply caption format"""
        for run in paragraph.runs:
            run.font.size = Pt(9)
            run.italic = True
            run.font.color.rgb = RGBColor(102, 102, 102)

    def get_style(self, style_type: str) -> Optional[str]:
        """
        Get style name if available in template

        Args:
            style_type: Type of style ('Heading 1', 'Normal', etc.)

        Returns:
            Style name if available, None otherwise
        """
        if style_type in self._available_styles:
            return style_type

        # Try variations
        variations = [
            style_type,
            style_type.replace(' ', ''),
            f"{style_type} Char",
            f"Heading{style_type.split()[-1]}" if 'Heading' in style_type else None
        ]

        for variation in variations:
            if variation and variation in self._available_styles:
                return variation

        return None

    def has_style(self, style_name: str) -> bool:
        """
        Check if style exists in template

        Args:
            style_name: Style name to check

        Returns:
            True if style exists
        """
        return style_name in self._available_styles

    def apply_ypf_branding(self, paragraph: Any) -> None:
        """
        Apply YPF brand colors to paragraph

        Args:
            paragraph: Paragraph object
        """
        # YPF brand colors: Dark Blue (#1A365D), Green (#00A859)
        for run in paragraph.runs:
            if run.bold:
                run.font.color.rgb = RGBColor(26, 54, 93)  # YPF Dark Blue
            elif run.italic:
                run.font.color.rgb = RGBColor(0, 168, 89)  # YPF Green

    def get_available_styles(self) -> list:
        """
        Get list of available styles

        Returns:
            List of style names
        """
        return sorted(list(self._available_styles))

    def create_table_style(self, table: Any) -> None:
        """
        Apply YPF corporate table styling

        Args:
            table: Table object
        """
        try:
            # Try to apply template table style
            if 'Table Grid' in self._available_styles:
                table.style = 'Table Grid'
            elif 'Light Grid' in self._available_styles:
                table.style = 'Light Grid'
            elif 'Medium Grid 1' in self._available_styles:
                table.style = 'Medium Grid 1'

            # Apply YPF colors to header row
            if len(table.rows) > 0:
                header_cells = table.rows[0].cells
                for cell in header_cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.bold = True
                            run.font.color.rgb = RGBColor(255, 255, 255)
                        # Set cell background (requires XML manipulation)
                        # This is simplified - full implementation would use python-docx-template

        except Exception as e:
            logger.warning(f"Could not apply table style: {e}")
