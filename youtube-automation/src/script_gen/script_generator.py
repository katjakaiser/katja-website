"""
Skript-Generierung für YouTube-Videos mit Anthropic Claude.

Workflow:
1. Du lädst Quellen in NotebookLM hoch
2. NotebookLM generiert eine Zusammenfassung/Podcast
3. Du fügst den Text hier ein
4. Claude optimiert das Skript für YouTube
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VideoScript:
    """Ein generiertes Video-Skript."""

    title: str
    hook: str  # Eröffnung (erste 10 Sekunden)
    introduction: str
    main_content: list[dict]  # Liste von Abschnitten
    conclusion: str
    call_to_action: str

    # Metadaten
    target_duration_minutes: int = 10
    language: str = "de"
    tags: list[str] = field(default_factory=list)
    description: str = ""
    thumbnail_ideas: list[str] = field(default_factory=list)

    @property
    def full_script(self) -> str:
        """Gibt das vollständige Skript als Text zurück."""
        sections = [self.hook, "", self.introduction, ""]

        for section in self.main_content:
            sections.append(f"## {section.get('title', '')}")
            sections.append(section.get("content", ""))
            sections.append("")

        sections.extend(["", self.conclusion, "", self.call_to_action])

        return "\n".join(sections)

    @property
    def word_count(self) -> int:
        return len(self.full_script.split())

    @property
    def estimated_duration_minutes(self) -> float:
        """Geschätzte Sprechdauer (ca. 150 Wörter/Minute)."""
        return self.word_count / 150

    @property
    def estimated_characters(self) -> int:
        """Geschätzte Zeichenanzahl (für ElevenLabs-Kosten)."""
        return len(self.full_script)

    def to_dict(self) -> dict:
        """Konvertiert das Skript in ein Dictionary."""
        return {
            "title": self.title,
            "hook": self.hook,
            "introduction": self.introduction,
            "main_content": self.main_content,
            "conclusion": self.conclusion,
            "call_to_action": self.call_to_action,
            "target_duration_minutes": self.target_duration_minutes,
            "language": self.language,
            "tags": self.tags,
            "description": self.description,
            "thumbnail_ideas": self.thumbnail_ideas,
            "word_count": self.word_count,
            "estimated_duration_minutes": round(self.estimated_duration_minutes, 1),
            "estimated_characters": self.estimated_characters,
        }

    def save(self, file_path: Path | str) -> None:
        """Speichert das Skript als JSON."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "VideoScript":
        """Erstellt ein VideoScript aus einem Dictionary."""
        return cls(
            title=data["title"],
            hook=data["hook"],
            introduction=data["introduction"],
            main_content=data["main_content"],
            conclusion=data["conclusion"],
            call_to_action=data["call_to_action"],
            target_duration_minutes=data.get("target_duration_minutes", 10),
            language=data.get("language", "de"),
            tags=data.get("tags", []),
            description=data.get("description", ""),
            thumbnail_ideas=data.get("thumbnail_ideas", []),
        )

    @classmethod
    def from_plain_text(cls, text: str, title: str = "Video") -> "VideoScript":
        """
        Erstellt ein einfaches VideoScript aus reinem Text.

        Nützlich wenn du bereits ein fertiges Skript hast
        (z.B. direkt aus NotebookLM).
        """
        return cls(
            title=title,
            hook="",
            introduction="",
            main_content=[{"title": "Hauptteil", "content": text}],
            conclusion="",
            call_to_action="",
        )


class ScriptGenerator:
    """
    Generiert und optimiert Video-Skripte mit Anthropic Claude.

    Workflow:
        1. NotebookLM: Quellen hochladen, Zusammenfassung generieren
        2. Hier: Text einfügen, Claude optimiert für YouTube

    Beispiel:
        generator = ScriptGenerator(api_key="sk-ant-...")

        # NotebookLM-Text zu YouTube-Skript optimieren
        script = generator.optimize_for_youtube(
            notebooklm_text="Dein NotebookLM-Output...",
            topic="Stressmanagement",
        )

        # Oder direkt ein Skript generieren
        script = generator.generate_script(
            source_text="Deine Quellen...",
            topic="Stressmanagement",
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.model = model
        self._client = None
        self._api_key = api_key

    def _get_client(self):
        """Lazy-Loading des Anthropic-Clients."""
        if self._client is not None:
            return self._client

        from anthropic import Anthropic

        self._client = Anthropic(api_key=self._api_key)
        return self._client

    def optimize_for_youtube(
        self,
        notebooklm_text: str,
        topic: str,
        target_duration_minutes: int = 10,
        style: str = "professional",
        additional_instructions: str = "",
    ) -> VideoScript:
        """
        Optimiert NotebookLM-Output für YouTube.

        Dies ist der Hauptworkflow:
        1. Du generierst Text/Podcast in NotebookLM
        2. Kopierst den Text hierher
        3. Claude strukturiert ihn als YouTube-Skript

        Args:
            notebooklm_text: Der Text aus NotebookLM
            topic: Das Hauptthema
            target_duration_minutes: Ziel-Videolänge
            style: Stil (professional, casual, educational)
            additional_instructions: Zusätzliche Anweisungen

        Returns:
            VideoScript-Objekt
        """
        logger.info(f"Optimiere NotebookLM-Text für YouTube: {topic}")

        target_words = target_duration_minutes * 150

        prompt = f"""Optimiere den folgenden Text aus NotebookLM für ein YouTube-Video.

NOTEBOOKLM-TEXT:
{notebooklm_text}

THEMA: {topic}
ZIEL-LÄNGE: ca. {target_words} Wörter (~{target_duration_minutes} Minuten)
STIL: {self._get_style_desc(style)}
SPRECHER: Katja Kaiser - Executive Coach für Performance, Leadership und Breathwork

{f"ZUSÄTZLICHE ANWEISUNGEN: {additional_instructions}" if additional_instructions else ""}

Strukturiere den Text als YouTube-Video-Skript im JSON-Format:

{{
    "title": "Aussagekräftiger Video-Titel (max. 60 Zeichen)",
    "hook": "Aufmerksamkeitsstarker Einstieg - die ersten 10 Sekunden entscheiden! (max. 50 Wörter)",
    "introduction": "Was erwartet die Zuschauer? Warum sollten sie dranbleiben? (ca. 100 Wörter)",
    "main_content": [
        {{
            "title": "Kapitel 1: [Überschrift]",
            "content": "Inhalt zum Vorlesen..."
        }},
        {{
            "title": "Kapitel 2: [Überschrift]",
            "content": "Inhalt zum Vorlesen..."
        }}
    ],
    "conclusion": "Zusammenfassung der wichtigsten Punkte (ca. 100 Wörter)",
    "call_to_action": "Was sollen Zuschauer als nächstes tun? Abonnieren, kommentieren, etc. (ca. 50 Wörter)",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "description": "YouTube-Beschreibung für unter dem Video (2-3 Sätze)",
    "thumbnail_ideas": ["Thumbnail-Idee 1", "Thumbnail-Idee 2"]
}}

WICHTIG:
- Schreibe zum VORLESEN, nicht zum Lesen
- Natürliche, gesprochene Sprache
- Kurze Sätze, klare Struktur
- Sprich Zuschauer direkt an ("du", "dir")
- Baue rhetorische Fragen ein
- Antworte NUR mit dem JSON"""

        response = self._call_claude(prompt)
        return self._parse_response(response, topic, target_duration_minutes)

    def generate_script(
        self,
        source_text: str,
        topic: str,
        target_duration_minutes: int = 10,
        style: str = "professional",
        additional_instructions: str = "",
    ) -> VideoScript:
        """
        Generiert ein Video-Skript direkt aus Quellentext.

        Falls du NotebookLM nicht nutzen möchtest.

        Args:
            source_text: Der kombinierte Text aller Quellen
            topic: Das Hauptthema
            target_duration_minutes: Ziel-Videolänge
            style: Stil (professional, casual, educational)
            additional_instructions: Zusätzliche Anweisungen

        Returns:
            VideoScript-Objekt
        """
        logger.info(f"Generiere Skript für: {topic}")

        target_words = target_duration_minutes * 150

        prompt = f"""Erstelle ein YouTube-Video-Skript basierend auf den folgenden Quellen.

QUELLEN:
{source_text[:20000]}

THEMA: {topic}
ZIEL-LÄNGE: ca. {target_words} Wörter (~{target_duration_minutes} Minuten)
STIL: {self._get_style_desc(style)}
SPRECHER: Katja Kaiser - Executive Coach für Performance, Leadership und Breathwork

{f"ZUSÄTZLICHE ANWEISUNGEN: {additional_instructions}" if additional_instructions else ""}

Erstelle das Skript im JSON-Format:

{{
    "title": "Aussagekräftiger Video-Titel",
    "hook": "Aufmerksamkeitsstarker Einstieg (erste 10 Sekunden, max. 50 Wörter)",
    "introduction": "Einleitung (ca. 100 Wörter)",
    "main_content": [
        {{"title": "Kapitel 1", "content": "..."}},
        {{"title": "Kapitel 2", "content": "..."}}
    ],
    "conclusion": "Zusammenfassung (ca. 100 Wörter)",
    "call_to_action": "Handlungsaufforderung (ca. 50 Wörter)",
    "tags": ["tag1", "tag2", "tag3"],
    "description": "YouTube-Beschreibung (2-3 Sätze)",
    "thumbnail_ideas": ["Idee 1", "Idee 2"]
}}

WICHTIG: Schreibe zum VORLESEN, natürliche Sprache, sprich Zuschauer direkt an.
Antworte NUR mit dem JSON."""

        response = self._call_claude(prompt)
        script = self._parse_response(response, topic, target_duration_minutes)

        logger.info(
            f"Skript generiert: {script.word_count} Wörter, "
            f"~{script.estimated_duration_minutes:.1f} Minuten, "
            f"~{script.estimated_characters} Zeichen"
        )

        return script

    def _get_style_desc(self, style: str) -> str:
        """Gibt Stil-Beschreibung zurück."""
        styles = {
            "professional": "professionell, kompetent aber nahbar",
            "casual": "locker, freundlich, wie ein Gespräch unter Freunden",
            "educational": "lehrreich, didaktisch aufgebaut, mit klaren Erklärungen",
        }
        return styles.get(style, styles["professional"])

    def _call_claude(self, prompt: str) -> str:
        """Ruft Claude API auf."""
        client = self._get_client()

        system_message = """Du bist ein erfahrener Skriptautor für YouTube-Videos im Bereich
Executive Coaching, Leadership und persönliche Entwicklung.

Der Sprecher ist Katja Kaiser, eine Executive Coach mit Expertise in:
- Executive Performance & High Performance
- Leadership Development
- Breathwork & Stressmanagement
- Mindset & Selbstführung

Erstelle Skripte, die:
- Wissenschaftlich fundiert aber leicht verständlich sind
- Zum VORLESEN geeignet sind (natürliche Sprache)
- Die Zuschauer direkt ansprechen
- Mit einem starken Hook beginnen
- Klare Handlungsempfehlungen geben

Antworte immer im angeforderten JSON-Format."""

        response = client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system_message,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _parse_response(
        self, response: str, topic: str, target_duration: int
    ) -> VideoScript:
        """Parst die Claude-Antwort in ein VideoScript-Objekt."""

        # JSON aus der Antwort extrahieren
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            raise ValueError("Keine gültige JSON-Antwort von Claude erhalten")

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON-Parsing fehlgeschlagen: {e}")

        return VideoScript(
            title=data.get("title", topic),
            hook=data.get("hook", ""),
            introduction=data.get("introduction", ""),
            main_content=data.get("main_content", []),
            conclusion=data.get("conclusion", ""),
            call_to_action=data.get("call_to_action", ""),
            target_duration_minutes=target_duration,
            language="de",
            tags=data.get("tags", []),
            description=data.get("description", ""),
            thumbnail_ideas=data.get("thumbnail_ideas", []),
        )

    def refine_script(
        self,
        script: VideoScript,
        feedback: str,
    ) -> VideoScript:
        """
        Überarbeitet ein Skript basierend auf Feedback.

        Args:
            script: Das ursprüngliche Skript
            feedback: Feedback zur Überarbeitung

        Returns:
            Überarbeitetes VideoScript
        """
        prompt = f"""Überarbeite das folgende Video-Skript basierend auf dem Feedback.

AKTUELLES SKRIPT:
{json.dumps(script.to_dict(), ensure_ascii=False, indent=2)}

FEEDBACK:
{feedback}

Gib das überarbeitete Skript im gleichen JSON-Format zurück.
Antworte NUR mit dem JSON-Objekt."""

        response = self._call_claude(prompt)
        return self._parse_response(response, script.title, script.target_duration_minutes)

    def generate_timestamps(self, script: VideoScript) -> list[dict]:
        """
        Generiert Zeitstempel-Kapitel für das Video.

        Args:
            script: Das Video-Skript

        Returns:
            Liste von Zeitstempeln mit Titel
        """
        timestamps = []
        current_time = 0

        # Hook + Intro
        timestamps.append({"time": "0:00", "title": "Einführung"})

        # Wörter pro Abschnitt zählen
        intro_words = len(script.hook.split()) + len(script.introduction.split())
        current_time += int(intro_words / 150 * 60)

        # Hauptabschnitte
        for section in script.main_content:
            minutes = current_time // 60
            seconds = current_time % 60
            timestamps.append({
                "time": f"{minutes}:{seconds:02d}",
                "title": section.get("title", "").replace("Kapitel", "").strip(": 0123456789"),
            })

            section_words = len(section.get("content", "").split())
            current_time += int(section_words / 150 * 60)

        # Fazit
        minutes = current_time // 60
        seconds = current_time % 60
        timestamps.append({"time": f"{minutes}:{seconds:02d}", "title": "Fazit & Zusammenfassung"})

        return timestamps
