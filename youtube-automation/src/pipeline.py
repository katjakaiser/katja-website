"""
Vollständige Video-Pipeline - Von Quellen zum YouTube-Upload.

Orchestriert den gesamten Prozess:
1. Quellen einlesen (PDFs, URLs)
2. Skript generieren
3. Audio synthesieren
4. Video erstellen
5. Auf YouTube hochladen
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .sources import SourceManager, SourceCollection
from .script_gen import ScriptGenerator, VideoScript
from .voice import VoiceSynthesizer, VoiceSettings
from .video import VideoGenerator, VideoConfig
from .upload import YouTubeUploader, VideoMetadata, UploadResult

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class PipelineConfig:
    """Konfiguration für die Video-Pipeline."""

    # Pfade
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    output_dir: Path = field(default_factory=lambda: Path("./data/videos"))

    # LLM
    llm_provider: Literal["openai", "anthropic"] = "openai"
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None

    # ElevenLabs
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    voice_settings: Optional[VoiceSettings] = None

    # YouTube
    youtube_client_secrets: Optional[Path] = None
    youtube_credentials: Optional[Path] = None
    default_privacy: Literal["private", "unlisted", "public"] = "private"

    # Video
    video_config: Optional[VideoConfig] = None

    # Skript
    default_video_length: int = 10  # Minuten
    default_language: str = "de"


@dataclass
class PipelineResult:
    """Ergebnis einer Pipeline-Ausführung."""

    success: bool
    video_path: Optional[Path] = None
    youtube_result: Optional[UploadResult] = None
    script: Optional[VideoScript] = None
    audio_path: Optional[Path] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary für JSON-Export."""
        return {
            "success": self.success,
            "video_path": str(self.video_path) if self.video_path else None,
            "youtube_url": self.youtube_result.video_url if self.youtube_result else None,
            "error": self.error_message,
            "execution_time_seconds": round(self.execution_time, 2),
        }


class VideoPipeline:
    """
    Vollständige Pipeline für automatisierte Video-Erstellung.

    Beispiel:
        pipeline = VideoPipeline(config)

        # Quellen hinzufügen
        pipeline.add_pdf("studie.pdf")
        pipeline.add_url("https://example.com/artikel")

        # Video erstellen
        result = pipeline.run(
            topic="Stressmanagement für Führungskräfte",
            upload_to_youtube=True
        )

        if result.success:
            print(f"Video-URL: {result.youtube_result.video_url}")
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()

        # Verzeichnisse erstellen
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Module initialisieren
        self.source_manager = SourceManager(data_dir=self.config.data_dir / "sources")
        self.script_generator = None
        self.voice_synthesizer = None
        self.video_generator = None
        self.youtube_uploader = None

        self._initialize_modules()

    def _initialize_modules(self):
        """Initialisiert die Module basierend auf der Konfiguration."""
        # Script Generator
        if self.config.llm_api_key:
            self.script_generator = ScriptGenerator(
                provider=self.config.llm_provider,
                model=self.config.llm_model,
                api_key=self.config.llm_api_key,
            )

        # Voice Synthesizer
        if self.config.elevenlabs_api_key and self.config.elevenlabs_voice_id:
            self.voice_synthesizer = VoiceSynthesizer(
                api_key=self.config.elevenlabs_api_key,
                voice_id=self.config.elevenlabs_voice_id,
                settings=self.config.voice_settings,
                output_dir=self.config.data_dir / "audio",
            )

        # Video Generator
        self.video_generator = VideoGenerator(
            config=self.config.video_config,
            output_dir=self.config.output_dir,
        )

        # YouTube Uploader
        if self.config.youtube_client_secrets:
            self.youtube_uploader = YouTubeUploader(
                client_secrets_file=self.config.youtube_client_secrets,
                credentials_file=self.config.youtube_credentials,
            )

    # === Quellen-Management ===

    def add_pdf(self, file_path: Path | str) -> None:
        """Fügt eine PDF-Datei als Quelle hinzu."""
        self.source_manager.add_pdf(file_path)
        console.print(f"[green]PDF hinzugefügt:[/green] {Path(file_path).name}")

    def add_pdfs_from_directory(self, directory: Path | str) -> None:
        """Fügt alle PDFs aus einem Verzeichnis hinzu."""
        results = self.source_manager.add_pdf_directory(directory)
        console.print(f"[green]{len(results)} PDFs hinzugefügt[/green]")

    def add_url(self, url: str) -> None:
        """Fügt eine URL als Quelle hinzu."""
        self.source_manager.add_url(url)
        console.print(f"[green]URL hinzugefügt:[/green] {url}")

    def add_urls(self, urls: list[str]) -> None:
        """Fügt mehrere URLs als Quellen hinzu."""
        self.source_manager.add_urls(urls)
        console.print(f"[green]{len(urls)} URLs hinzugefügt[/green]")

    def add_text(self, text: str, title: str = "") -> None:
        """Fügt einen Rohtext als Quelle hinzu."""
        self.source_manager.add_text(text, title)
        console.print(f"[green]Text hinzugefügt:[/green] {title or 'Ohne Titel'}")

    def get_source_statistics(self) -> dict:
        """Gibt Statistiken über die geladenen Quellen zurück."""
        return self.source_manager.get_statistics()

    # === Pipeline-Ausführung ===

    def run(
        self,
        topic: str,
        target_duration_minutes: int = None,
        style: str = "professional",
        additional_instructions: str = "",
        upload_to_youtube: bool = False,
        youtube_privacy: str = None,
        save_intermediate: bool = True,
    ) -> PipelineResult:
        """
        Führt die vollständige Video-Pipeline aus.

        Args:
            topic: Das Thema des Videos
            target_duration_minutes: Ziel-Videolänge
            style: Stil (professional, casual, educational)
            additional_instructions: Zusätzliche Anweisungen für die Skript-Generierung
            upload_to_youtube: Ob das Video hochgeladen werden soll
            youtube_privacy: Privacy-Status für YouTube
            save_intermediate: Ob Zwischenergebnisse gespeichert werden sollen

        Returns:
            PipelineResult mit allen Ergebnissen
        """
        import time

        start_time = time.time()
        target_duration = target_duration_minutes or self.config.default_video_length

        console.print(f"\n[bold blue]Video-Pipeline gestartet[/bold blue]")
        console.print(f"Thema: {topic}")
        console.print(f"Ziel-Länge: {target_duration} Minuten\n")

        try:
            # 1. Quellensammlung erstellen
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Quellen verarbeiten...", total=None)

                collection = self.source_manager.create_collection(
                    name=topic,
                    save=save_intermediate,
                )

                if collection.total_sources == 0:
                    raise ValueError("Keine Quellen geladen. Bitte zuerst Quellen hinzufügen.")

                progress.update(task, description=f"[green]✓[/green] {collection.total_sources} Quellen verarbeitet")

            # 2. Skript generieren
            if not self.script_generator:
                raise ValueError("LLM API Key nicht konfiguriert")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Skript generieren...", total=None)

                script = self.script_generator.generate_script(
                    source_text=collection.get_combined_text(),
                    topic=topic,
                    target_duration_minutes=target_duration,
                    style=style,
                    additional_instructions=additional_instructions,
                )

                if save_intermediate:
                    script_path = self.config.data_dir / "scripts" / f"{self._safe_filename(topic)}.json"
                    script_path.parent.mkdir(parents=True, exist_ok=True)
                    script.save(script_path)

                progress.update(
                    task,
                    description=f"[green]✓[/green] Skript generiert ({script.word_count} Wörter, ~{script.estimated_duration_minutes:.1f} Min)"
                )

            # 3. Audio synthesieren
            audio_path = None
            if self.voice_synthesizer:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Audio generieren...", total=None)

                    audio_filename = f"{self._safe_filename(topic)}.mp3"
                    audio_path = self.voice_synthesizer.synthesize_script_to_file(
                        text=script.full_script,
                        output_filename=audio_filename,
                    )

                    progress.update(task, description=f"[green]✓[/green] Audio generiert")
            else:
                console.print("[yellow]⚠ ElevenLabs nicht konfiguriert - Audio wird übersprungen[/yellow]")

            # 4. Video erstellen
            video_path = None
            if audio_path:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Video erstellen...", total=None)

                    # Key Points aus Skript extrahieren
                    key_points = [
                        section.get("title", "")
                        for section in script.main_content
                        if section.get("title")
                    ]

                    video_path = self.video_generator.create_video_with_key_points(
                        audio_path=audio_path,
                        title=script.title,
                        key_points=key_points,
                    )

                    progress.update(task, description=f"[green]✓[/green] Video erstellt")

            # 5. YouTube Upload
            youtube_result = None
            if upload_to_youtube and video_path:
                if not self.youtube_uploader:
                    console.print("[yellow]⚠ YouTube nicht konfiguriert - Upload wird übersprungen[/yellow]")
                else:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        task = progress.add_task("Auf YouTube hochladen...", total=None)

                        # Authentifizieren
                        self.youtube_uploader.authenticate()

                        # Beschreibung erstellen
                        description = self._create_youtube_description(script, collection)

                        metadata = VideoMetadata(
                            title=script.title,
                            description=description,
                            tags=script.tags,
                            privacy_status=youtube_privacy or self.config.default_privacy,
                            language=self.config.default_language,
                        )

                        youtube_result = self.youtube_uploader.upload(
                            video_path=video_path,
                            metadata=metadata,
                        )

                        if youtube_result.success:
                            progress.update(task, description=f"[green]✓[/green] Upload erfolgreich")
                        else:
                            progress.update(task, description=f"[red]✗[/red] Upload fehlgeschlagen")

            # Ergebnis zusammenstellen
            execution_time = time.time() - start_time

            result = PipelineResult(
                success=True,
                video_path=video_path,
                youtube_result=youtube_result,
                script=script,
                audio_path=audio_path,
                execution_time=execution_time,
            )

            # Zusammenfassung ausgeben
            self._print_summary(result)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"Pipeline-Fehler: {e}")
            console.print(f"\n[red]Fehler: {e}[/red]")

            return PipelineResult(
                success=False,
                error_message=str(e),
                execution_time=execution_time,
            )

    def _create_youtube_description(
        self,
        script: VideoScript,
        collection: SourceCollection,
    ) -> str:
        """Erstellt die YouTube-Beschreibung."""
        # Timestamps generieren
        timestamps = self.script_generator.generate_timestamps(script)
        timestamp_text = "\n".join(f"{t['time']} {t['title']}" for t in timestamps)

        # Quellen
        sources_text = "\n".join(collection.get_source_citations())

        description = f"""{script.description}

⏱️ Timestamps:
{timestamp_text}

📚 Quellen:
{sources_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 Website: https://katjakaiser-coaching.de
📧 Kontakt: kontakt@katjakaiser-coaching.de

#ExecutiveCoaching #Leadership #Performance #KatjaKaiser
"""
        return description

    def _print_summary(self, result: PipelineResult) -> None:
        """Gibt eine Zusammenfassung der Pipeline-Ausführung aus."""
        console.print("\n" + "=" * 50)
        console.print("[bold green]Pipeline abgeschlossen![/bold green]")
        console.print("=" * 50)

        if result.script:
            console.print(f"Titel: {result.script.title}")
            console.print(f"Skript: {result.script.word_count} Wörter")

        if result.audio_path:
            console.print(f"Audio: {result.audio_path}")

        if result.video_path:
            console.print(f"Video: {result.video_path}")

        if result.youtube_result and result.youtube_result.success:
            console.print(f"\n[bold]YouTube:[/bold]")
            console.print(f"  URL: {result.youtube_result.video_url}")
            console.print(f"  Studio: {result.youtube_result.youtube_studio_url}")

        console.print(f"\nAusführungszeit: {result.execution_time:.1f} Sekunden")

    def _safe_filename(self, name: str) -> str:
        """Erstellt einen sicheren Dateinamen."""
        return "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()[:50]

    def clear_sources(self) -> None:
        """Löscht alle geladenen Quellen."""
        self.source_manager.clear()
        console.print("[yellow]Alle Quellen gelöscht[/yellow]")


def create_pipeline_from_env() -> VideoPipeline:
    """
    Erstellt eine Pipeline mit Konfiguration aus Umgebungsvariablen.

    Erwartet folgende Umgebungsvariablen:
    - OPENAI_API_KEY oder ANTHROPIC_API_KEY
    - LLM_PROVIDER (optional, default: openai)
    - ELEVENLABS_API_KEY
    - ELEVENLABS_VOICE_ID
    - YOUTUBE_CLIENT_SECRETS_FILE
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    config = PipelineConfig(
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        llm_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
        youtube_client_secrets=Path(os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")),
    )

    return VideoPipeline(config)
