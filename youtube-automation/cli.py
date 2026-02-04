#!/usr/bin/env python3
"""
YouTube Video Automation CLI

Kommandozeilen-Interface für die automatisierte Video-Erstellung.

Verwendung:
    python cli.py create --topic "Mein Thema" --pdf dokument.pdf --url https://...
    python cli.py voice-clone --name "Katja" --samples audio1.mp3 audio2.mp3
    python cli.py list-voices
"""

import os
import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

# Projektpfad zum Python-Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline import VideoPipeline, PipelineConfig, create_pipeline_from_env
from src.voice import VoiceSynthesizer, VoiceCloneHelper

load_dotenv()

app = typer.Typer(
    name="youtube-auto",
    help="Automatisierte YouTube-Video-Erstellung aus Quellen",
    add_completion=False,
)
console = Console()


@app.command()
def create(
    topic: str = typer.Option(..., "--topic", "-t", help="Thema des Videos"),
    pdfs: List[Path] = typer.Option([], "--pdf", "-p", help="PDF-Dateien als Quellen"),
    urls: List[str] = typer.Option([], "--url", "-u", help="URLs als Quellen"),
    pdf_dir: Optional[Path] = typer.Option(None, "--pdf-dir", help="Verzeichnis mit PDFs"),
    duration: int = typer.Option(10, "--duration", "-d", help="Ziel-Videolänge in Minuten"),
    style: str = typer.Option("professional", "--style", "-s", help="Stil: professional, casual, educational"),
    upload: bool = typer.Option(False, "--upload", help="Direkt auf YouTube hochladen"),
    privacy: str = typer.Option("private", "--privacy", help="YouTube Privacy: private, unlisted, public"),
    instructions: str = typer.Option("", "--instructions", "-i", help="Zusätzliche Anweisungen"),
):
    """
    Erstellt ein Video aus den angegebenen Quellen.

    Beispiel:
        python cli.py create -t "Stressmanagement" -p studie.pdf -u https://example.com
    """
    console.print("[bold]YouTube Video Automation[/bold]\n")

    # Pipeline erstellen
    try:
        pipeline = create_pipeline_from_env()
    except Exception as e:
        console.print(f"[red]Konfigurationsfehler: {e}[/red]")
        console.print("Bitte .env Datei prüfen (siehe .env.example)")
        raise typer.Exit(1)

    # Quellen hinzufügen
    if not pdfs and not urls and not pdf_dir:
        console.print("[red]Keine Quellen angegeben![/red]")
        console.print("Verwende --pdf, --url oder --pdf-dir")
        raise typer.Exit(1)

    for pdf in pdfs:
        if pdf.exists():
            pipeline.add_pdf(pdf)
        else:
            console.print(f"[yellow]PDF nicht gefunden: {pdf}[/yellow]")

    if pdf_dir and pdf_dir.is_dir():
        pipeline.add_pdfs_from_directory(pdf_dir)

    for url in urls:
        pipeline.add_url(url)

    # Statistiken anzeigen
    stats = pipeline.get_source_statistics()
    console.print(f"\n[bold]Geladene Quellen:[/bold]")
    console.print(f"  PDFs: {stats['pdfs']['count']} ({stats['pdfs']['total_words']} Wörter)")
    console.print(f"  URLs: {stats['web_pages']['count']} ({stats['web_pages']['total_words']} Wörter)")

    # Pipeline ausführen
    result = pipeline.run(
        topic=topic,
        target_duration_minutes=duration,
        style=style,
        additional_instructions=instructions,
        upload_to_youtube=upload,
        youtube_privacy=privacy,
    )

    if not result.success:
        console.print(f"\n[red]Pipeline fehlgeschlagen: {result.error_message}[/red]")
        raise typer.Exit(1)

    console.print("\n[green]Fertig![/green]")


@app.command("voice-clone")
def voice_clone(
    name: str = typer.Option(..., "--name", "-n", help="Name für die geklonte Stimme"),
    samples: List[Path] = typer.Option(..., "--sample", "-s", help="Audio-Sample-Dateien"),
    description: str = typer.Option("", "--description", "-d", help="Beschreibung der Stimme"),
):
    """
    Klont eine Stimme aus Audio-Samples.

    Beispiel:
        python cli.py voice-clone -n "Katja" -s sample1.mp3 -s sample2.mp3
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        console.print("[red]ELEVENLABS_API_KEY nicht gesetzt![/red]")
        raise typer.Exit(1)

    # Samples prüfen
    valid_samples = []
    for sample in samples:
        if sample.exists():
            valid_samples.append(sample)
        else:
            console.print(f"[yellow]Sample nicht gefunden: {sample}[/yellow]")

    if not valid_samples:
        console.print("[red]Keine gültigen Audio-Samples gefunden![/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Voice Cloning: {name}[/bold]")
    console.print(f"Samples: {len(valid_samples)}")

    # Anleitung anzeigen
    console.print("\n" + VoiceCloneHelper.prepare_samples_guide())

    if not typer.confirm("\nMit Voice Cloning fortfahren?"):
        raise typer.Exit(0)

    synth = VoiceSynthesizer(api_key=api_key, voice_id="placeholder")

    try:
        voice_id = synth.clone_voice(
            name=name,
            audio_files=valid_samples,
            description=description or f"Geklonte Stimme: {name}",
        )

        console.print(f"\n[green]Stimme erfolgreich geklont![/green]")
        console.print(f"Voice ID: [bold]{voice_id}[/bold]")
        console.print("\nFüge diese ID zu deiner .env hinzu:")
        console.print(f"ELEVENLABS_VOICE_ID={voice_id}")

    except Exception as e:
        console.print(f"[red]Voice Cloning fehlgeschlagen: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-voices")
def list_voices():
    """
    Listet alle verfügbaren ElevenLabs-Stimmen auf.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        console.print("[red]ELEVENLABS_API_KEY nicht gesetzt![/red]")
        raise typer.Exit(1)

    synth = VoiceSynthesizer(api_key=api_key, voice_id="placeholder")

    try:
        voices = synth.list_available_voices()

        table = Table(title="Verfügbare Stimmen")
        table.add_column("Voice ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Kategorie")
        table.add_column("Labels")

        for voice in voices:
            labels = ", ".join(f"{k}: {v}" for k, v in (voice.get("labels") or {}).items())
            table.add_row(
                voice["voice_id"],
                voice["name"],
                voice.get("category", ""),
                labels[:50] + "..." if len(labels) > 50 else labels,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Fehler: {e}[/red]")
        raise typer.Exit(1)


@app.command("test-voice")
def test_voice(
    text: str = typer.Option("Hallo, ich bin Katja Kaiser. Willkommen zu meinem Video über Executive Coaching.", "--text", "-t"),
    output: Path = typer.Option(Path("test_audio.mp3"), "--output", "-o"),
):
    """
    Testet die konfigurierte Stimme mit einem kurzen Text.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")

    if not api_key or not voice_id:
        console.print("[red]ELEVENLABS_API_KEY und ELEVENLABS_VOICE_ID müssen gesetzt sein![/red]")
        raise typer.Exit(1)

    console.print(f"Generiere Audio für: '{text[:50]}...'")

    synth = VoiceSynthesizer(api_key=api_key, voice_id=voice_id)

    try:
        segment = synth.synthesize(text, output_path=output)
        console.print(f"[green]Audio gespeichert: {output}[/green]")
        console.print(f"Geschätzte Dauer: {segment.duration_seconds:.1f} Sekunden")

    except Exception as e:
        console.print(f"[red]Fehler: {e}[/red]")
        raise typer.Exit(1)


@app.command("youtube-auth")
def youtube_auth():
    """
    Authentifiziert bei YouTube (öffnet Browser).
    """
    from src.upload import YouTubeUploader

    client_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

    if not Path(client_secrets).exists():
        console.print(f"[red]client_secrets.json nicht gefunden: {client_secrets}[/red]")
        console.print("\nAnleitung:")
        console.print("1. Gehe zu https://console.cloud.google.com")
        console.print("2. YouTube Data API v3 aktivieren")
        console.print("3. OAuth2 Client ID erstellen (Desktop App)")
        console.print("4. JSON herunterladen als 'client_secrets.json'")
        raise typer.Exit(1)

    uploader = YouTubeUploader(client_secrets_file=client_secrets)

    try:
        uploader.authenticate()
        info = uploader.get_channel_info()

        console.print(f"\n[green]Erfolgreich authentifiziert![/green]")
        console.print(f"\nKanal: {info.get('title', 'Unbekannt')}")
        console.print(f"Abonnenten: {info.get('subscriber_count', 'N/A')}")
        console.print(f"Videos: {info.get('video_count', 'N/A')}")

    except Exception as e:
        console.print(f"[red]Authentifizierung fehlgeschlagen: {e}[/red]")
        raise typer.Exit(1)


@app.command("setup")
def setup():
    """
    Interaktiver Setup-Assistent für die Konfiguration.
    """
    console.print("[bold]YouTube Video Automation - Setup[/bold]\n")

    env_content = []

    # LLM Provider
    console.print("[bold]1. LLM Provider[/bold]")
    provider = typer.prompt("Welchen LLM-Provider möchtest du nutzen?", default="openai", type=str)
    env_content.append(f"LLM_PROVIDER={provider}")

    if provider == "openai":
        api_key = typer.prompt("OpenAI API Key", hide_input=True)
        env_content.append(f"OPENAI_API_KEY={api_key}")
    else:
        api_key = typer.prompt("Anthropic API Key", hide_input=True)
        env_content.append(f"ANTHROPIC_API_KEY={api_key}")

    # ElevenLabs
    console.print("\n[bold]2. ElevenLabs Voice Cloning[/bold]")
    if typer.confirm("ElevenLabs konfigurieren?", default=True):
        el_key = typer.prompt("ElevenLabs API Key", hide_input=True)
        env_content.append(f"ELEVENLABS_API_KEY={el_key}")

        if typer.confirm("Hast du bereits eine Voice ID?"):
            voice_id = typer.prompt("Voice ID")
            env_content.append(f"ELEVENLABS_VOICE_ID={voice_id}")
        else:
            console.print("Nutze 'python cli.py voice-clone' um eine Stimme zu klonen")

    # YouTube
    console.print("\n[bold]3. YouTube Upload[/bold]")
    if typer.confirm("YouTube Upload konfigurieren?", default=True):
        console.print("Du benötigst eine client_secrets.json von Google Cloud Console")
        if typer.confirm("Hast du die Datei bereits?"):
            path = typer.prompt("Pfad zur client_secrets.json", default="client_secrets.json")
            env_content.append(f"YOUTUBE_CLIENT_SECRETS_FILE={path}")

    # .env speichern
    env_path = Path(".env")
    if env_path.exists() and not typer.confirm("\n.env existiert bereits. Überschreiben?"):
        console.print("Setup abgebrochen")
        raise typer.Exit(0)

    with open(env_path, "w") as f:
        f.write("\n".join(env_content))

    console.print(f"\n[green]Konfiguration gespeichert in {env_path}[/green]")
    console.print("\nNächste Schritte:")
    console.print("1. python cli.py voice-clone  (Stimme klonen)")
    console.print("2. python cli.py youtube-auth (YouTube authentifizieren)")
    console.print("3. python cli.py create       (Video erstellen)")


@app.command("info")
def info():
    """
    Zeigt Informationen über die aktuelle Konfiguration.
    """
    console.print("[bold]YouTube Video Automation - Konfiguration[/bold]\n")

    table = Table(title="Umgebungsvariablen")
    table.add_column("Variable", style="cyan")
    table.add_column("Status", style="green")

    checks = [
        ("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")),
        ("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY")),
        ("ELEVENLABS_API_KEY", os.getenv("ELEVENLABS_API_KEY")),
        ("ELEVENLABS_VOICE_ID", os.getenv("ELEVENLABS_VOICE_ID")),
        ("YOUTUBE_CLIENT_SECRETS_FILE", os.getenv("YOUTUBE_CLIENT_SECRETS_FILE")),
    ]

    for name, value in checks:
        if value:
            status = "[green]✓ Konfiguriert[/green]"
            if "KEY" in name:
                status += f" ({value[:8]}...)"
        else:
            status = "[red]✗ Nicht gesetzt[/red]"
        table.add_row(name, status)

    console.print(table)

    # Dateien prüfen
    console.print("\n[bold]Dateien:[/bold]")
    files = [
        (".env", Path(".env")),
        ("client_secrets.json", Path(os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"))),
        ("youtube_credentials.pickle", Path("youtube_credentials.pickle")),
    ]

    for name, path in files:
        if path.exists():
            console.print(f"  [green]✓[/green] {name}")
        else:
            console.print(f"  [red]✗[/red] {name}")


if __name__ == "__main__":
    app()
