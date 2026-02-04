"""
PDF-Verarbeitung für die Quellenextraktion.
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import pdfplumber
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class PDFContent:
    """Extrahierter Inhalt aus einer PDF-Datei."""

    file_path: Path
    title: str
    text: str
    num_pages: int
    metadata: dict = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def get_summary_text(self, max_chars: int = 500) -> str:
        """Gibt eine Kurzfassung des Textes zurück."""
        if len(self.text) <= max_chars:
            return self.text
        return self.text[:max_chars] + "..."


class PDFProcessor:
    """Verarbeitet PDF-Dateien und extrahiert Text und Metadaten."""

    def __init__(self):
        self.processed_pdfs: list[PDFContent] = []

    def process_file(self, file_path: Path | str) -> PDFContent:
        """
        Verarbeitet eine einzelne PDF-Datei.

        Args:
            file_path: Pfad zur PDF-Datei

        Returns:
            PDFContent mit extrahiertem Text und Metadaten
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"PDF nicht gefunden: {file_path}")

        if not file_path.suffix.lower() == ".pdf":
            raise ValueError(f"Keine PDF-Datei: {file_path}")

        logger.info(f"Verarbeite PDF: {file_path.name}")

        # Versuche zuerst mit pdfplumber (bessere Textextraktion)
        text = self._extract_with_pdfplumber(file_path)

        # Fallback zu PyPDF2 wenn pdfplumber fehlschlägt
        if not text.strip():
            logger.warning("pdfplumber konnte keinen Text extrahieren, versuche PyPDF2...")
            text = self._extract_with_pypdf2(file_path)

        # Metadaten extrahieren
        metadata = self._extract_metadata(file_path)
        num_pages = metadata.get("num_pages", 0)

        # Titel aus Metadaten oder Dateiname
        title = metadata.get("title") or file_path.stem

        content = PDFContent(
            file_path=file_path,
            title=title,
            text=self._clean_text(text),
            num_pages=num_pages,
            metadata=metadata,
        )

        self.processed_pdfs.append(content)
        logger.info(f"PDF verarbeitet: {content.word_count} Wörter aus {num_pages} Seiten")

        return content

    def process_directory(self, directory: Path | str) -> list[PDFContent]:
        """
        Verarbeitet alle PDFs in einem Verzeichnis.

        Args:
            directory: Pfad zum Verzeichnis

        Returns:
            Liste von PDFContent-Objekten
        """
        directory = Path(directory)

        if not directory.is_dir():
            raise NotADirectoryError(f"Kein Verzeichnis: {directory}")

        pdf_files = list(directory.glob("*.pdf"))
        logger.info(f"Gefunden: {len(pdf_files)} PDF-Dateien in {directory}")

        results = []
        for pdf_file in pdf_files:
            try:
                content = self.process_file(pdf_file)
                results.append(content)
            except Exception as e:
                logger.error(f"Fehler bei {pdf_file.name}: {e}")

        return results

    def _extract_with_pdfplumber(self, file_path: Path) -> str:
        """Extrahiert Text mit pdfplumber (bessere Qualität)."""
        text_parts = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        except Exception as e:
            logger.warning(f"pdfplumber Fehler: {e}")
            return ""

        return "\n\n".join(text_parts)

    def _extract_with_pypdf2(self, file_path: Path) -> str:
        """Extrahiert Text mit PyPDF2 (Fallback)."""
        text_parts = []

        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        except Exception as e:
            logger.error(f"PyPDF2 Fehler: {e}")
            return ""

        return "\n\n".join(text_parts)

    def _extract_metadata(self, file_path: Path) -> dict:
        """Extrahiert Metadaten aus der PDF."""
        metadata = {}

        try:
            reader = PdfReader(file_path)
            metadata["num_pages"] = len(reader.pages)

            if reader.metadata:
                metadata["title"] = reader.metadata.get("/Title")
                metadata["author"] = reader.metadata.get("/Author")
                metadata["subject"] = reader.metadata.get("/Subject")
                metadata["creator"] = reader.metadata.get("/Creator")
                metadata["creation_date"] = reader.metadata.get("/CreationDate")

        except Exception as e:
            logger.warning(f"Metadaten-Extraktion fehlgeschlagen: {e}")

        return metadata

    def _clean_text(self, text: str) -> str:
        """Bereinigt extrahierten Text."""
        # Mehrfache Leerzeichen/Zeilenumbrüche reduzieren
        import re

        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\t+", " ", text)

        # Seitenumbruch-Artefakte entfernen
        text = re.sub(r"-\n", "", text)  # Silbentrennung

        return text.strip()

    def get_combined_text(self) -> str:
        """Gibt den kombinierten Text aller verarbeiteten PDFs zurück."""
        return "\n\n---\n\n".join(
            f"# {pdf.title}\n\n{pdf.text}" for pdf in self.processed_pdfs
        )
