"""
Source Manager - Vereinheitlichte Verwaltung aller Quellentypen.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Union

from .pdf_processor import PDFProcessor, PDFContent
from .web_processor import WebProcessor, WebContent, StudyProcessor

logger = logging.getLogger(__name__)


@dataclass
class SourceCollection:
    """Eine Sammlung von Quellen für ein Video."""

    name: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    pdfs: list[PDFContent] = field(default_factory=list)
    web_pages: list[WebContent] = field(default_factory=list)
    raw_texts: list[dict] = field(default_factory=list)

    @property
    def total_sources(self) -> int:
        return len(self.pdfs) + len(self.web_pages) + len(self.raw_texts)

    @property
    def total_word_count(self) -> int:
        pdf_words = sum(pdf.word_count for pdf in self.pdfs)
        web_words = sum(web.word_count for web in self.web_pages)
        raw_words = sum(len(t.get("text", "").split()) for t in self.raw_texts)
        return pdf_words + web_words + raw_words

    def get_combined_text(self) -> str:
        """Kombiniert alle Quelltexte für die LLM-Verarbeitung."""
        sections = []

        # PDFs
        for pdf in self.pdfs:
            sections.append(
                f"## Quelle: {pdf.title} (PDF)\n"
                f"Datei: {pdf.file_path.name}\n\n"
                f"{pdf.text}"
            )

        # Webseiten
        for web in self.web_pages:
            sections.append(
                f"## Quelle: {web.title} (Web)\n"
                f"URL: {web.url}\n\n"
                f"{web.text}"
            )

        # Rohtexte
        for raw in self.raw_texts:
            title = raw.get("title", "Ohne Titel")
            sections.append(
                f"## Quelle: {title} (Text)\n\n"
                f"{raw.get('text', '')}"
            )

        return "\n\n---\n\n".join(sections)

    def get_source_citations(self) -> list[str]:
        """Gibt eine Liste der Quellenzitate zurück."""
        citations = []

        for pdf in self.pdfs:
            citations.append(f"- {pdf.title} (PDF)")

        for web in self.web_pages:
            citations.append(f"- {web.title}: {web.url}")

        for raw in self.raw_texts:
            if title := raw.get("title"):
                citations.append(f"- {title}")

        return citations

    def to_dict(self) -> dict:
        """Konvertiert die Sammlung in ein Dictionary für JSON-Export."""
        return {
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "total_sources": self.total_sources,
            "total_word_count": self.total_word_count,
            "pdfs": [
                {
                    "file_path": str(pdf.file_path),
                    "title": pdf.title,
                    "num_pages": pdf.num_pages,
                    "word_count": pdf.word_count,
                }
                for pdf in self.pdfs
            ],
            "web_pages": [
                {
                    "url": web.url,
                    "title": web.title,
                    "domain": web.domain,
                    "word_count": web.word_count,
                }
                for web in self.web_pages
            ],
            "raw_texts": [
                {
                    "title": t.get("title", ""),
                    "word_count": len(t.get("text", "").split()),
                }
                for t in self.raw_texts
            ],
        }


class SourceManager:
    """
    Zentraler Manager für alle Quellenverarbeitung.

    Beispiel:
        manager = SourceManager()

        # PDFs hinzufügen
        manager.add_pdf("dokument.pdf")
        manager.add_pdf_directory("./studien/")

        # URLs hinzufügen
        manager.add_url("https://example.com/artikel")
        manager.add_urls(["url1", "url2", "url3"])

        # Rohtexte hinzufügen
        manager.add_text("Mein eigener Text...", title="Notizen")

        # Sammlung erstellen
        collection = manager.create_collection("Mein Video")
    """

    def __init__(self, data_dir: Path | str | None = None):
        self.pdf_processor = PDFProcessor()
        self.web_processor = WebProcessor()
        self.study_processor = StudyProcessor()

        self.data_dir = Path(data_dir) if data_dir else Path("./data/sources")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._raw_texts: list[dict] = []

    def add_pdf(self, file_path: Path | str) -> PDFContent:
        """Fügt eine PDF-Datei hinzu."""
        return self.pdf_processor.process_file(file_path)

    def add_pdf_directory(self, directory: Path | str) -> list[PDFContent]:
        """Fügt alle PDFs aus einem Verzeichnis hinzu."""
        return self.pdf_processor.process_directory(directory)

    def add_url(self, url: str) -> WebContent:
        """Fügt eine URL hinzu."""
        # Prüfe ob es eine Studien-URL ist
        if self.study_processor.is_study_url(url):
            return self.study_processor.process_url(url)
        return self.web_processor.process_url(url)

    def add_urls(self, urls: list[str]) -> list[WebContent]:
        """Fügt mehrere URLs hinzu."""
        results = []
        for url in urls:
            try:
                content = self.add_url(url)
                results.append(content)
            except Exception as e:
                logger.error(f"Fehler bei URL {url}: {e}")
        return results

    def add_text(self, text: str, title: str = "") -> None:
        """Fügt einen Rohtext hinzu."""
        self._raw_texts.append({
            "title": title,
            "text": text,
            "added_at": datetime.now().isoformat(),
        })
        logger.info(f"Text hinzugefügt: {title or 'Ohne Titel'} ({len(text.split())} Wörter)")

    def create_collection(
        self,
        name: str,
        description: str = "",
        save: bool = True,
    ) -> SourceCollection:
        """
        Erstellt eine Quellensammlung aus allen hinzugefügten Quellen.

        Args:
            name: Name der Sammlung
            description: Optionale Beschreibung
            save: Ob die Sammlung gespeichert werden soll

        Returns:
            SourceCollection mit allen Quellen
        """
        collection = SourceCollection(
            name=name,
            description=description,
            pdfs=self.pdf_processor.processed_pdfs.copy(),
            web_pages=(
                self.web_processor.processed_urls.copy()
                + self.study_processor.processed_urls.copy()
            ),
            raw_texts=self._raw_texts.copy(),
        )

        logger.info(
            f"Sammlung erstellt: {name} - "
            f"{collection.total_sources} Quellen, "
            f"{collection.total_word_count} Wörter"
        )

        if save:
            self._save_collection(collection)

        return collection

    def _save_collection(self, collection: SourceCollection) -> Path:
        """Speichert eine Quellensammlung als JSON."""
        # Sicheren Dateinamen erstellen
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in collection.name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.json"

        file_path = self.data_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(collection.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"Sammlung gespeichert: {file_path}")
        return file_path

    def load_collection(self, file_path: Path | str) -> dict:
        """Lädt eine gespeicherte Quellensammlung."""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def clear(self) -> None:
        """Löscht alle verarbeiteten Quellen."""
        self.pdf_processor = PDFProcessor()
        self.web_processor = WebProcessor()
        self.study_processor = StudyProcessor()
        self._raw_texts = []
        logger.info("Alle Quellen gelöscht")

    def get_statistics(self) -> dict:
        """Gibt Statistiken über alle verarbeiteten Quellen zurück."""
        return {
            "pdfs": {
                "count": len(self.pdf_processor.processed_pdfs),
                "total_pages": sum(
                    pdf.num_pages for pdf in self.pdf_processor.processed_pdfs
                ),
                "total_words": sum(
                    pdf.word_count for pdf in self.pdf_processor.processed_pdfs
                ),
            },
            "web_pages": {
                "count": len(self.web_processor.processed_urls),
                "total_words": sum(
                    web.word_count for web in self.web_processor.processed_urls
                ),
            },
            "studies": {
                "count": len(self.study_processor.processed_urls),
                "total_words": sum(
                    web.word_count for web in self.study_processor.processed_urls
                ),
            },
            "raw_texts": {
                "count": len(self._raw_texts),
                "total_words": sum(
                    len(t.get("text", "").split()) for t in self._raw_texts
                ),
            },
        }
