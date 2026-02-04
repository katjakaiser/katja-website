"""
Quellenverarbeitung - PDFs, URLs, Text
"""

from .pdf_processor import PDFProcessor
from .web_processor import WebProcessor
from .source_manager import SourceManager

__all__ = ["PDFProcessor", "WebProcessor", "SourceManager"]
