"""
Web-Inhaltsverarbeitung für URLs und Studien.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Versuche trafilatura für bessere Extraktion
try:
    import trafilatura

    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

logger = logging.getLogger(__name__)


@dataclass
class WebContent:
    """Extrahierter Inhalt von einer Webseite."""

    url: str
    title: str
    text: str
    domain: str
    metadata: dict = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def get_summary_text(self, max_chars: int = 500) -> str:
        """Gibt eine Kurzfassung des Textes zurück."""
        if len(self.text) <= max_chars:
            return self.text
        return self.text[:max_chars] + "..."


class WebProcessor:
    """Verarbeitet Webseiten und extrahiert relevante Inhalte."""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.processed_urls: list[WebContent] = []
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

    def process_url(self, url: str) -> WebContent:
        """
        Verarbeitet eine URL und extrahiert den Hauptinhalt.

        Args:
            url: Die zu verarbeitende URL

        Returns:
            WebContent mit extrahiertem Text und Metadaten
        """
        logger.info(f"Verarbeite URL: {url}")

        # URL validieren
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Ungültiges URL-Schema: {parsed.scheme}")

        # Seite abrufen
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Fehler beim Abrufen der URL: {e}")

        # Content-Type prüfen
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type.lower():
            logger.warning(f"Unerwarteter Content-Type: {content_type}")

        # Text extrahieren
        html = response.text

        if HAS_TRAFILATURA:
            text = self._extract_with_trafilatura(html, url)
        else:
            text = self._extract_with_beautifulsoup(html)

        # Titel extrahieren
        title = self._extract_title(html, url)

        # Metadaten extrahieren
        metadata = self._extract_metadata(html)

        content = WebContent(
            url=url,
            title=title,
            text=self._clean_text(text),
            domain=parsed.netloc,
            metadata=metadata,
        )

        self.processed_urls.append(content)
        logger.info(f"URL verarbeitet: {content.word_count} Wörter von {content.domain}")

        return content

    def process_urls(self, urls: list[str]) -> list[WebContent]:
        """
        Verarbeitet mehrere URLs.

        Args:
            urls: Liste von URLs

        Returns:
            Liste von WebContent-Objekten
        """
        results = []

        for url in urls:
            try:
                content = self.process_url(url)
                results.append(content)
            except Exception as e:
                logger.error(f"Fehler bei URL {url}: {e}")

        return results

    def _extract_with_trafilatura(self, html: str, url: str) -> str:
        """Extrahiert Text mit trafilatura (beste Qualität)."""
        try:
            text = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
            )
            return text or ""
        except Exception as e:
            logger.warning(f"trafilatura Fehler: {e}")
            return self._extract_with_beautifulsoup(html)

    def _extract_with_beautifulsoup(self, html: str) -> str:
        """Extrahiert Text mit BeautifulSoup (Fallback)."""
        soup = BeautifulSoup(html, "html.parser")

        # Unerwünschte Elemente entfernen
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # Versuche Hauptinhalt zu finden
        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find(class_=re.compile(r"content|article|post|entry"))
            or soup.find("body")
        )

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        return text

    def _extract_title(self, html: str, url: str) -> str:
        """Extrahiert den Titel der Seite."""
        soup = BeautifulSoup(html, "html.parser")

        # Verschiedene Titel-Quellen prüfen
        title = None

        # 1. Open Graph Title
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content")

        # 2. Title Tag
        if not title:
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.string

        # 3. H1
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        # 4. URL als Fallback
        if not title:
            title = urlparse(url).path.split("/")[-1] or urlparse(url).netloc

        return title.strip() if title else "Ohne Titel"

    def _extract_metadata(self, html: str) -> dict:
        """Extrahiert Metadaten aus der Seite."""
        soup = BeautifulSoup(html, "html.parser")
        metadata = {}

        # Meta Description
        desc = soup.find("meta", attrs={"name": "description"})
        if desc:
            metadata["description"] = desc.get("content")

        # Author
        author = soup.find("meta", attrs={"name": "author"})
        if author:
            metadata["author"] = author.get("content")

        # Published Date
        date_meta = soup.find("meta", property="article:published_time")
        if date_meta:
            metadata["published_date"] = date_meta.get("content")

        # Keywords
        keywords = soup.find("meta", attrs={"name": "keywords"})
        if keywords:
            metadata["keywords"] = keywords.get("content")

        return metadata

    def _clean_text(self, text: str) -> str:
        """Bereinigt extrahierten Text."""
        # Mehrfache Leerzeichen/Zeilenumbrüche reduzieren
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\t+", " ", text)

        # Leere Zeilen am Anfang/Ende entfernen
        lines = [line.strip() for line in text.split("\n")]
        lines = [line for line in lines if line]

        return "\n".join(lines)

    def get_combined_text(self) -> str:
        """Gibt den kombinierten Text aller verarbeiteten URLs zurück."""
        return "\n\n---\n\n".join(
            f"# {web.title}\nQuelle: {web.url}\n\n{web.text}"
            for web in self.processed_urls
        )


class StudyProcessor(WebProcessor):
    """
    Spezialisierter Processor für wissenschaftliche Studien.
    Unterstützt PubMed, Google Scholar, und andere Quellen.
    """

    STUDY_DOMAINS = [
        "pubmed.ncbi.nlm.nih.gov",
        "scholar.google.com",
        "researchgate.net",
        "sciencedirect.com",
        "nature.com",
        "springer.com",
        "wiley.com",
        "tandfonline.com",
        "frontiersin.org",
    ]

    def is_study_url(self, url: str) -> bool:
        """Prüft, ob die URL eine wissenschaftliche Quelle ist."""
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in self.STUDY_DOMAINS)

    def extract_citation_info(self, content: WebContent) -> dict:
        """Extrahiert Zitationsinformationen aus einer Studie."""
        citation = {
            "title": content.title,
            "url": content.url,
            "authors": content.metadata.get("author", ""),
            "date": content.metadata.get("published_date", ""),
        }

        # DOI extrahieren wenn vorhanden
        doi_match = re.search(r"10\.\d{4,}/[^\s]+", content.text)
        if doi_match:
            citation["doi"] = doi_match.group(0)

        return citation
