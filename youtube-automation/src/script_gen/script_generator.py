"""
Skript-Generierung für YouTube-Videos mit LLM-Unterstützung.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

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


class ScriptGenerator:
    """
    Generiert Video-Skripte aus Quelleninhalten mit LLM-Unterstützung.

    Unterstützt OpenAI und Anthropic APIs.
    """

    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = provider
        self.model = model
        self._client = None
        self._api_key = api_key

        # Standard-Modelle
        if not self.model:
            self.model = (
                "gpt-4-turbo-preview" if provider == "openai" else "claude-3-5-sonnet-20241022"
            )

    def _get_client(self):
        """Lazy-Loading des API-Clients."""
        if self._client is not None:
            return self._client

        if self.provider == "openai":
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key)
        else:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self._api_key)

        return self._client

    def generate_script(
        self,
        source_text: str,
        topic: str,
        target_duration_minutes: int = 10,
        style: str = "professional",
        additional_instructions: str = "",
    ) -> VideoScript:
        """
        Generiert ein Video-Skript aus dem Quellentext.

        Args:
            source_text: Der kombinierte Text aller Quellen
            topic: Das Hauptthema des Videos
            target_duration_minutes: Ziel-Videolänge in Minuten
            style: Stil des Videos (professional, casual, educational)
            additional_instructions: Zusätzliche Anweisungen

        Returns:
            VideoScript-Objekt
        """
        logger.info(f"Generiere Skript für: {topic}")

        # Ziel-Wortanzahl berechnen (ca. 150 Wörter/Minute)
        target_words = target_duration_minutes * 150

        prompt = self._build_prompt(
            source_text=source_text,
            topic=topic,
            target_words=target_words,
            style=style,
            additional_instructions=additional_instructions,
        )

        # LLM aufrufen
        response = self._call_llm(prompt)

        # Antwort parsen
        script = self._parse_response(response, topic, target_duration_minutes)

        logger.info(
            f"Skript generiert: {script.word_count} Wörter, "
            f"~{script.estimated_duration_minutes:.1f} Minuten"
        )

        return script

    def _build_prompt(
        self,
        source_text: str,
        topic: str,
        target_words: int,
        style: str,
        additional_instructions: str,
    ) -> str:
        """Erstellt den Prompt für die Skript-Generierung."""

        style_instructions = {
            "professional": "professionell, kompetent aber nahbar",
            "casual": "locker, freundlich, wie ein Gespräch unter Freunden",
            "educational": "lehrreich, didaktisch aufgebaut, mit klaren Erklärungen",
        }

        style_desc = style_instructions.get(style, style_instructions["professional"])

        prompt = f"""Erstelle ein YouTube-Video-Skript basierend auf den folgenden Quellen.

THEMA: {topic}

ZIEL-LÄNGE: ca. {target_words} Wörter (für ein ~{target_words // 150} Minuten Video)

STIL: {style_desc}

SPRECHER: Katja Kaiser - Executive Coach für Performance, Leadership und Breathwork

QUELLEN:
{source_text[:15000]}  # Begrenzen um Token-Limit nicht zu überschreiten

{f"ZUSÄTZLICHE ANWEISUNGEN: {additional_instructions}" if additional_instructions else ""}

Erstelle das Skript im folgenden JSON-Format:

{{
    "title": "Aussagekräftiger Video-Titel",
    "hook": "Aufmerksamkeitsstarker Einstieg (erste 10 Sekunden, max. 50 Wörter)",
    "introduction": "Einleitung - Was erwartet die Zuschauer? (ca. 100 Wörter)",
    "main_content": [
        {{
            "title": "Abschnitt 1: [Überschrift]",
            "content": "Inhalt des Abschnitts..."
        }},
        {{
            "title": "Abschnitt 2: [Überschrift]",
            "content": "Inhalt des Abschnitts..."
        }}
        // Weitere Abschnitte nach Bedarf
    ],
    "conclusion": "Zusammenfassung und Key Takeaways (ca. 100 Wörter)",
    "call_to_action": "Handlungsaufforderung am Ende (ca. 50 Wörter)",
    "tags": ["tag1", "tag2", "tag3"],
    "description": "YouTube-Beschreibung (2-3 Sätze)",
    "thumbnail_ideas": ["Idee 1", "Idee 2"]
}}

WICHTIG:
- Das Skript sollte zum Vorlesen geeignet sein
- Verwende natürliche Sprache, keine Aufzählungen
- Baue wissenschaftliche Erkenntnisse aus den Quellen ein
- Gib praktische Tipps und Handlungsempfehlungen
- Sprich die Zuschauer direkt an ("du", "dir")
- Antworte NUR mit dem JSON-Objekt, keine zusätzlichen Erklärungen
"""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Ruft das LLM mit dem Prompt auf."""
        client = self._get_client()

        system_message = """Du bist ein erfahrener Skriptautor für YouTube-Videos im Bereich
Executive Coaching, Leadership und persönliche Entwicklung.

Der Sprecher ist Katja Kaiser, eine Executive Coach mit Expertise in:
- Executive Performance
- Leadership Development
- Breathwork & Stressmanagement
- Mindset & Selbstführung

Erstelle Skripte, die wissenschaftlich fundiert, aber leicht verständlich sind.
Antworte immer im angeforderten JSON-Format."""

        if self.provider == "openai":
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=4000,
            )
            return response.choices[0].message.content

        else:  # anthropic
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
        """Parst die LLM-Antwort in ein VideoScript-Objekt."""

        # JSON aus der Antwort extrahieren
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            raise ValueError("Keine gültige JSON-Antwort vom LLM erhalten")

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON-Parsing fehlgeschlagen: {e}")

        # VideoScript erstellen
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

        response = self._call_llm(prompt)
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
                "title": section.get("title", "").replace("Abschnitt", "").strip(": 0123456789"),
            })

            section_words = len(section.get("content", "").split())
            current_time += int(section_words / 150 * 60)

        # Fazit
        minutes = current_time // 60
        seconds = current_time % 60
        timestamps.append({"time": f"{minutes}:{seconds:02d}", "title": "Fazit & Zusammenfassung"})

        return timestamps
