"""
Voice Synthesis mit ElevenLabs API.

Unterstützt Voice Cloning für personalisierte Stimmen.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Generator
import io

logger = logging.getLogger(__name__)


@dataclass
class VoiceSettings:
    """Einstellungen für die Sprachsynthese."""

    stability: float = 0.5  # 0.0 = variabel, 1.0 = stabil
    similarity_boost: float = 0.75  # Ähnlichkeit zur Originalstimme
    style: float = 0.0  # Stil-Übertreibung (0.0 - 1.0)
    use_speaker_boost: bool = True


@dataclass
class AudioSegment:
    """Ein generiertes Audio-Segment."""

    text: str
    audio_data: bytes
    duration_seconds: float
    file_path: Optional[Path] = None


class VoiceSynthesizer:
    """
    Synthesiert Sprache mit ElevenLabs API.

    Beispiel:
        synth = VoiceSynthesizer(
            api_key="...",
            voice_id="..."
        )

        # Einfache Synthese
        audio = synth.synthesize("Hallo, ich bin Katja.")
        audio.save("output.mp3")

        # Langes Skript in Segmenten
        for segment in synth.synthesize_long_text(script, chunk_size=500):
            segment.save(f"segment_{i}.mp3")
    """

    # ElevenLabs Modelle
    MODELS = {
        "multilingual_v2": "eleven_multilingual_v2",  # Beste Qualität, mehrsprachig
        "turbo_v2_5": "eleven_turbo_v2_5",  # Schneller, gut für Englisch
        "turbo_v2": "eleven_turbo_v2",  # Schnell, mehrsprachig
    }

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model: str = "multilingual_v2",
        settings: Optional[VoiceSettings] = None,
        output_dir: Optional[Path | str] = None,
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = self.MODELS.get(model, model)
        self.settings = settings or VoiceSettings()
        self.output_dir = Path(output_dir) if output_dir else Path("./data/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._client = None

    def _get_client(self):
        """Lazy-Loading des ElevenLabs-Clients."""
        if self._client is None:
            from elevenlabs import ElevenLabs

            self._client = ElevenLabs(api_key=self.api_key)
        return self._client

    def synthesize(
        self,
        text: str,
        output_path: Optional[Path | str] = None,
    ) -> AudioSegment:
        """
        Synthesiert Text zu Audio.

        Args:
            text: Der zu synthetisierende Text
            output_path: Optionaler Speicherpfad

        Returns:
            AudioSegment mit den Audio-Daten
        """
        logger.info(f"Synthesiere {len(text)} Zeichen...")
        client = self._get_client()

        # Audio generieren
        audio_generator = client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id=self.model_id,
            voice_settings={
                "stability": self.settings.stability,
                "similarity_boost": self.settings.similarity_boost,
                "style": self.settings.style,
                "use_speaker_boost": self.settings.use_speaker_boost,
            },
        )

        # Audio-Daten sammeln
        audio_data = b"".join(audio_generator)

        # Dauer schätzen (ca. 150 Wörter/Minute)
        word_count = len(text.split())
        estimated_duration = word_count / 150 * 60

        segment = AudioSegment(
            text=text,
            audio_data=audio_data,
            duration_seconds=estimated_duration,
        )

        # Speichern wenn Pfad angegeben
        if output_path:
            self._save_audio(segment, output_path)

        logger.info(f"Audio generiert: ~{estimated_duration:.1f} Sekunden")
        return segment

    def synthesize_long_text(
        self,
        text: str,
        chunk_size: int = 1000,
        pause_between_chunks: float = 0.5,
    ) -> Generator[AudioSegment, None, None]:
        """
        Synthesiert langen Text in Chunks.

        ElevenLabs hat ein Zeichenlimit pro Request.
        Diese Methode teilt den Text in sinnvolle Abschnitte.

        Args:
            text: Der vollständige Text
            chunk_size: Maximale Zeichen pro Chunk
            pause_between_chunks: Pause zwischen API-Calls (Rate-Limiting)

        Yields:
            AudioSegment für jeden Chunk
        """
        chunks = self._split_text(text, chunk_size)
        logger.info(f"Text in {len(chunks)} Chunks aufgeteilt")

        for i, chunk in enumerate(chunks):
            logger.info(f"Verarbeite Chunk {i + 1}/{len(chunks)}")

            segment = self.synthesize(chunk)
            yield segment

            # Rate-Limiting
            if i < len(chunks) - 1:
                time.sleep(pause_between_chunks)

    def synthesize_script_to_file(
        self,
        text: str,
        output_filename: str,
        chunk_size: int = 1000,
    ) -> Path:
        """
        Synthesiert ein vollständiges Skript und speichert es.

        Args:
            text: Das vollständige Skript
            output_filename: Name der Ausgabedatei (ohne Pfad)
            chunk_size: Maximale Zeichen pro Chunk

        Returns:
            Pfad zur kombinierten Audio-Datei
        """
        from pydub import AudioSegment as PydubSegment

        logger.info(f"Synthesiere Skript ({len(text)} Zeichen) zu {output_filename}")

        # Alle Chunks generieren
        audio_segments = []
        for segment in self.synthesize_long_text(text, chunk_size):
            audio_segments.append(segment)

        # Audio-Dateien kombinieren
        combined = PydubSegment.empty()
        for segment in audio_segments:
            audio = PydubSegment.from_mp3(io.BytesIO(segment.audio_data))
            combined += audio

        # Speichern
        output_path = self.output_dir / output_filename
        combined.export(output_path, format="mp3", bitrate="192k")

        logger.info(f"Audio gespeichert: {output_path}")
        return output_path

    def _split_text(self, text: str, max_chars: int) -> list[str]:
        """
        Teilt Text intelligent an Satzgrenzen.

        Args:
            text: Der zu teilende Text
            max_chars: Maximale Zeichen pro Chunk

        Returns:
            Liste von Text-Chunks
        """
        # Nach Absätzen trennen
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # Wenn Absatz zu lang, nach Sätzen trennen
            if len(para) > max_chars:
                sentences = self._split_into_sentences(para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < max_chars:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + " "
            else:
                if len(current_chunk) + len(para) < max_chars:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Teilt Text in Sätze."""
        import re

        # Einfache Satztrennung an ., !, ?
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _save_audio(self, segment: AudioSegment, path: Path | str) -> None:
        """Speichert ein Audio-Segment."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            f.write(segment.audio_data)

        segment.file_path = path
        logger.info(f"Audio gespeichert: {path}")

    def list_available_voices(self) -> list[dict]:
        """Listet alle verfügbaren Stimmen auf."""
        client = self._get_client()
        voices = client.voices.get_all()

        return [
            {
                "voice_id": v.voice_id,
                "name": v.name,
                "category": v.category,
                "labels": v.labels,
            }
            for v in voices.voices
        ]

    def clone_voice(
        self,
        name: str,
        audio_files: list[Path | str],
        description: str = "",
    ) -> str:
        """
        Klont eine Stimme aus Audio-Samples.

        Args:
            name: Name für die geklonte Stimme
            audio_files: Liste von Audio-Dateien (mind. 1 Minute gesamt)
            description: Optionale Beschreibung

        Returns:
            Voice ID der geklonten Stimme
        """
        client = self._get_client()

        # Dateien vorbereiten
        files = []
        for audio_file in audio_files:
            path = Path(audio_file)
            if not path.exists():
                raise FileNotFoundError(f"Audio-Datei nicht gefunden: {path}")
            files.append(open(path, "rb"))

        try:
            voice = client.voices.add(
                name=name,
                files=files,
                description=description or f"Geklonte Stimme: {name}",
            )

            logger.info(f"Stimme geklont: {voice.voice_id}")
            return voice.voice_id

        finally:
            for f in files:
                f.close()


class VoiceCloneHelper:
    """
    Hilfsfunktionen für das Voice Cloning.

    Tipps für beste Ergebnisse:
    - Mindestens 1-3 Minuten sauberes Audio
    - Keine Hintergrundgeräusche
    - Natürliche Sprechweise
    - Verschiedene Sätze und Emotionen
    """

    @staticmethod
    def prepare_samples_guide() -> str:
        """Gibt Anleitungen zur Vorbereitung von Voice-Samples."""
        return """
# Anleitung: Audio-Samples für Voice Cloning

## Anforderungen
- **Länge**: Mindestens 1-3 Minuten (mehr = besser)
- **Format**: MP3, WAV, M4A
- **Qualität**: Mindestens 44.1kHz, 16-bit

## Aufnahme-Tipps
1. **Ruhige Umgebung** - Keine Hintergrundgeräusche
2. **Gutes Mikrofon** - USB-Mikrofon oder Headset reicht
3. **Natürliche Sprache** - Wie in einem normalen Gespräch
4. **Abwechslung** - Verschiedene Sätze, Fragen, Aussagen
5. **Keine Musik** - Nur Sprache

## Beispiel-Skript zum Einsprechen
"Hallo, ich bin [Name]. Heute möchte ich über ein wichtiges Thema sprechen.
Wussten Sie, dass Atmung einen enormen Einfluss auf unsere Leistungsfähigkeit hat?
Das klingt vielleicht überraschend, aber es stimmt tatsächlich.
Lassen Sie mich Ihnen erklären, wie das funktioniert.
Fragen Sie sich manchmal, warum manche Tage besser laufen als andere?
Die Antwort könnte einfacher sein, als Sie denken!"

## Dateien benennen
- katja_sample_1.mp3
- katja_sample_2.mp3
- etc.
"""

    @staticmethod
    def recommended_settings_for_coaching() -> VoiceSettings:
        """Empfohlene Einstellungen für Coaching-Videos."""
        return VoiceSettings(
            stability=0.6,  # Leicht erhöht für ruhigere Stimme
            similarity_boost=0.8,  # Hohe Ähnlichkeit
            style=0.1,  # Minimal für natürlichen Klang
            use_speaker_boost=True,
        )
