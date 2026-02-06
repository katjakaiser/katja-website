#!/usr/bin/env python3
"""
YouTube Video Automation CLI

Workflow:
1. NotebookLM: Quellen hochladen, Zusammenfassung/Podcast generieren
2. Hier: NotebookLM-Text einfügen -> Claude optimiert -> Video erstellen -> YouTube hochladen

Verwendung:
    python cli.py from-notebooklm --topic "Mein Thema" --text "NotebookLM Output..."
    python cli.py voice-clone --name "Katja" --sample audio1.mp3 --sample audio2.mp3
    python cli.py full-pipeline --topic "Thema" --text "Text..."
"""

import os
import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

from src.voice.license_checker import LicenseChecker, COMMERCIAL_USE_WARNING

# Projektpfad zum Python-Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

app = typer.Typer(
    name="youtube-auto",
    help="Automatisierte YouTube-Video-Erstellung mit NotebookLM + Claude + ElevenLabs",
    add_completion=False,
)
console = Console()


def _check_elevenlabs_license(api_key: str) -> bool:
    """
    Prüft die ElevenLabs-Lizenz vor der Nutzung.

    Returns:
        True wenn kommerzielle Nutzung erlaubt, sonst False
    """
    console.print(Panel.fit(
        "[bold yellow]Lizenzprüfung[/bold yellow]\n"
        "Prüfe ElevenLabs Abo-Status...",
        border_style="yellow"
    ))

    checker = LicenseChecker(api_key=api_key)
    allowed, message = checker.verify_commercial_use()

    if not allowed:
        console.print(f"\n[bold red]{message}[/bold red]")
        console.print("\n" + COMMERCIAL_USE_WARNING)
        console.print("[red]Video-Erstellung wird abgebrochen.[/red]")
        console.print("[yellow]Bitte aktiviere ein kostenpflichtiges ElevenLabs-Abo (mind. Starter $5/Monat).[/yellow]")
        return False

    console.print(f"[green]{message}[/green]\n")
    return True


@app.command("from-notebooklm")
def from_notebooklm(
    topic: str = typer.Option(..., "--topic", "-t", help="Thema des Videos"),
    text_file: Optional[Path] = typer.Option(None, "--file", "-f", help="Textdatei mit NotebookLM-Output"),
    text: Optional[str] = typer.Option(None, "--text", help="NotebookLM-Text direkt"),
    duration: int = typer.Option(10, "--duration", "-d", help="Ziel-Videolänge in Minuten"),
    style: str = typer.Option("professional", "--style", "-s", help="Stil: professional, casual, educational"),
    output_script: Optional[Path] = typer.Option(None, "--output", "-o", help="Skript-Ausgabedatei"),
    generate_video: bool = typer.Option(False, "--video", "-v", help="Auch Video generieren"),
    upload: bool = typer.Option(False, "--upload", "-u", help="Auf YouTube hochladen"),
):
    """
    Erstellt ein YouTube-Skript aus NotebookLM-Output.

    Workflow:
    1. Quellen in NotebookLM hochladen
    2. Zusammenfassung oder Audio Overview generieren
    3. Text kopieren und hier einfügen

    Beispiel:
        python cli.py from-notebooklm -t "Stressmanagement" -f notebooklm_output.txt
        python cli.py from-notebooklm -t "Stressmanagement" --text "Dein Text..."
    """
    from src.script_gen import ScriptGenerator

    console.print(Panel.fit(
        "[bold]YouTube Video Automation[/bold]\n"
        "NotebookLM -> Claude -> Video -> YouTube",
        border_style="blue"
    ))

    # API Key prüfen
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY nicht gesetzt![/red]")
        console.print("Bitte in .env eintragen oder: export ANTHROPIC_API_KEY=...")
        raise typer.Exit(1)

    # Text laden
    if text_file and text_file.exists():
        notebooklm_text = text_file.read_text(encoding="utf-8")
        console.print(f"[green]Text geladen aus: {text_file}[/green]")
    elif text:
        notebooklm_text = text
    else:
        console.print("[yellow]Kein Text angegeben. Bitte NotebookLM-Output eingeben:[/yellow]")
        console.print("(Beende mit Ctrl+D oder einer leeren Zeile)")
        lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
        except EOFError:
            pass
        notebooklm_text = "\n".join(lines)

    if not notebooklm_text.strip():
        console.print("[red]Kein Text zum Verarbeiten![/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Input:[/bold] {len(notebooklm_text)} Zeichen")

    # Skript generieren
    console.print("\n[bold]Schritt 1:[/bold] Claude optimiert für YouTube...")
    generator = ScriptGenerator(api_key=api_key)

    script = generator.optimize_for_youtube(
        notebooklm_text=notebooklm_text,
        topic=topic,
        target_duration_minutes=duration,
        style=style,
    )

    console.print(f"[green]Skript generiert:[/green]")
    console.print(f"  Titel: {script.title}")
    console.print(f"  Wörter: {script.word_count}")
    console.print(f"  Dauer: ~{script.estimated_duration_minutes:.1f} Minuten")
    console.print(f"  Zeichen: {script.estimated_characters} (für ElevenLabs)")

    # Skript speichern
    if output_script:
        script.save(output_script)
        console.print(f"[green]Skript gespeichert: {output_script}[/green]")
    else:
        default_path = Path(f"data/scripts/{topic.replace(' ', '_')}.json")
        default_path.parent.mkdir(parents=True, exist_ok=True)
        script.save(default_path)
        console.print(f"[green]Skript gespeichert: {default_path}[/green]")

    # Video generieren?
    if generate_video or upload:
        _generate_video_from_script(script, upload)

    console.print("\n[green]Fertig![/green]")


@app.command("full-pipeline")
def full_pipeline(
    topic: str = typer.Option(..., "--topic", "-t", help="Thema des Videos"),
    text_file: Optional[Path] = typer.Option(None, "--file", "-f", help="Textdatei mit NotebookLM-Output"),
    duration: int = typer.Option(10, "--duration", "-d", help="Ziel-Videolänge in Minuten"),
    privacy: str = typer.Option("private", "--privacy", help="YouTube Privacy: private, unlisted, public"),
):
    """
    Führt die komplette Pipeline aus: NotebookLM-Text -> Skript -> Audio -> Video -> YouTube

    Beispiel:
        python cli.py full-pipeline -t "Stressmanagement" -f notebooklm.txt
    """
    from src.script_gen import ScriptGenerator
    from src.voice import VoiceSynthesizer
    from src.video import VideoGenerator
    from src.upload import YouTubeUploader, VideoMetadata

    console.print(Panel.fit(
        "[bold]Vollständige Video-Pipeline[/bold]\n"
        "NotebookLM -> Claude -> ElevenLabs -> Video -> YouTube",
        border_style="green"
    ))

    # Konfiguration prüfen
    api_key = os.getenv("ANTHROPIC_API_KEY")
    el_key = os.getenv("ELEVENLABS_API_KEY")
    el_voice = os.getenv("ELEVENLABS_VOICE_ID")
    yt_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

    missing = []
    if not api_key:
        missing.append("ANTHROPIC_API_KEY")
    if not el_key:
        missing.append("ELEVENLABS_API_KEY")
    if not el_voice:
        missing.append("ELEVENLABS_VOICE_ID")

    if missing:
        console.print(f"[red]Fehlende Konfiguration: {', '.join(missing)}[/red]")
        console.print("Nutze 'python cli.py setup' für die Einrichtung")
        raise typer.Exit(1)

    # LIZENZPRÜFUNG: Vor jeder kommerziellen Nutzung
    if not _check_elevenlabs_license(el_key):
        raise typer.Exit(1)

    # Text laden
    if text_file and text_file.exists():
        notebooklm_text = text_file.read_text(encoding="utf-8")
    else:
        console.print("[yellow]Bitte NotebookLM-Output eingeben (Ctrl+D zum Beenden):[/yellow]")
        notebooklm_text = sys.stdin.read()

    # 1. Skript generieren
    console.print("\n[bold]1/4[/bold] Skript generieren mit Claude...")
    generator = ScriptGenerator(api_key=api_key)
    script = generator.optimize_for_youtube(notebooklm_text, topic, duration)
    console.print(f"[green]✓[/green] Skript: {script.word_count} Wörter, ~{script.estimated_duration_minutes:.1f} Min")

    # 2. Audio generieren
    console.print("\n[bold]2/4[/bold] Audio generieren mit ElevenLabs...")
    synth = VoiceSynthesizer(api_key=el_key, voice_id=el_voice)
    audio_path = synth.synthesize_script_to_file(
        text=script.full_script,
        output_filename=f"{topic.replace(' ', '_')}.mp3"
    )
    console.print(f"[green]✓[/green] Audio: {audio_path}")

    # 3. Video erstellen
    console.print("\n[bold]3/4[/bold] Video erstellen...")
    video_gen = VideoGenerator()
    key_points = [s.get("title", "") for s in script.main_content]
    video_path = video_gen.create_video_with_key_points(
        audio_path=audio_path,
        title=script.title,
        key_points=key_points,
    )
    console.print(f"[green]✓[/green] Video: {video_path}")

    # 4. YouTube Upload
    console.print("\n[bold]4/4[/bold] Auf YouTube hochladen...")
    if not Path(yt_secrets).exists():
        console.print(f"[yellow]⚠ {yt_secrets} nicht gefunden - Upload übersprungen[/yellow]")
        console.print("Nutze 'python cli.py youtube-auth' für die Einrichtung")
    else:
        uploader = YouTubeUploader(client_secrets_file=yt_secrets)
        uploader.authenticate()

        timestamps = generator.generate_timestamps(script)
        timestamp_text = "\n".join(f"{t['time']} {t['title']}" for t in timestamps)

        metadata = VideoMetadata(
            title=script.title,
            description=f"{script.description}\n\n⏱️ Timestamps:\n{timestamp_text}",
            tags=script.tags,
            privacy_status=privacy,
        )

        result = uploader.upload(video_path, metadata)

        if result.success:
            console.print(f"[green]✓[/green] YouTube: {result.video_url}")
            console.print(f"   Studio: {result.youtube_studio_url}")
        else:
            console.print(f"[red]✗[/red] Upload fehlgeschlagen: {result.error_message}")

    console.print("\n[bold green]Pipeline abgeschlossen![/bold green]")


def _generate_video_from_script(script, upload: bool = False):
    """Hilfsfunktion für Video-Generierung aus Skript."""
    from src.voice import VoiceSynthesizer
    from src.video import VideoGenerator
    from src.upload import YouTubeUploader, VideoMetadata

    el_key = os.getenv("ELEVENLABS_API_KEY")
    el_voice = os.getenv("ELEVENLABS_VOICE_ID")

    if not el_key or not el_voice:
        console.print("[yellow]ElevenLabs nicht konfiguriert - Video wird übersprungen[/yellow]")
        return

    # LIZENZPRÜFUNG: Vor jeder kommerziellen Nutzung
    if not _check_elevenlabs_license(el_key):
        console.print("[red]Video-Erstellung abgebrochen wegen fehlender Lizenz.[/red]")
        return

    # Audio
    console.print("\n[bold]Schritt 2:[/bold] Audio generieren...")
    synth = VoiceSynthesizer(api_key=el_key, voice_id=el_voice)
    audio_path = synth.synthesize_script_to_file(
        script.full_script,
        f"{script.title.replace(' ', '_')}.mp3"
    )
    console.print(f"[green]Audio erstellt: {audio_path}[/green]")

    # Video
    console.print("\n[bold]Schritt 3:[/bold] Video erstellen...")
    video_gen = VideoGenerator()
    key_points = [s.get("title", "") for s in script.main_content]
    video_path = video_gen.create_video_with_key_points(
        audio_path=audio_path,
        title=script.title,
        key_points=key_points,
    )
    console.print(f"[green]Video erstellt: {video_path}[/green]")

    # Upload
    if upload:
        console.print("\n[bold]Schritt 4:[/bold] YouTube Upload...")
        yt_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
        if Path(yt_secrets).exists():
            uploader = YouTubeUploader(client_secrets_file=yt_secrets)
            uploader.authenticate()
            metadata = VideoMetadata(
                title=script.title,
                description=script.description,
                tags=script.tags,
            )
            result = uploader.upload(video_path, metadata)
            if result.success:
                console.print(f"[green]Hochgeladen: {result.video_url}[/green]")
        else:
            console.print(f"[yellow]{yt_secrets} nicht gefunden[/yellow]")


@app.command("voice-clone")
def voice_clone(
    name: str = typer.Option(..., "--name", "-n", help="Name für die geklonte Stimme"),
    samples: List[Path] = typer.Option(..., "--sample", "-s", help="Audio-Sample-Dateien (mind. 1 Min)"),
    description: str = typer.Option("", "--description", "-d", help="Beschreibung der Stimme"),
):
    """
    Klont deine Stimme aus Audio-Samples (EINMALIG).

    Nach dem Klonen wird die Voice ID angezeigt - diese in .env eintragen.

    Beispiel:
        python cli.py voice-clone -n "Katja" -s sample1.mp3 -s sample2.mp3
    """
    from src.voice import VoiceSynthesizer, VoiceCloneHelper

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        console.print("[red]ELEVENLABS_API_KEY nicht gesetzt![/red]")
        raise typer.Exit(1)

    # Samples prüfen
    valid_samples = [s for s in samples if s.exists()]
    invalid = [s for s in samples if not s.exists()]

    for s in invalid:
        console.print(f"[yellow]Sample nicht gefunden: {s}[/yellow]")

    if not valid_samples:
        console.print("[red]Keine gültigen Audio-Samples gefunden![/red]")
        raise typer.Exit(1)

    console.print(Panel.fit(
        f"[bold]Voice Cloning: {name}[/bold]\n"
        f"Samples: {len(valid_samples)} Dateien\n\n"
        "[yellow]Hinweis:[/yellow] Das Klonen ist EINMALIG.\n"
        "Die monatlichen Kosten entstehen durch die NUTZUNG.",
        border_style="blue"
    ))

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

        console.print(f"\n[bold green]Stimme erfolgreich geklont![/bold green]")
        console.print(f"\nVoice ID: [bold cyan]{voice_id}[/bold cyan]")
        console.print("\n[yellow]Füge diese ID zu deiner .env hinzu:[/yellow]")
        console.print(f"ELEVENLABS_VOICE_ID={voice_id}")

    except Exception as e:
        console.print(f"[red]Voice Cloning fehlgeschlagen: {e}[/red]")
        raise typer.Exit(1)


@app.command("test-voice")
def test_voice(
    text: str = typer.Option(
        "Hallo, ich bin Katja Kaiser. Willkommen zu meinem Video über Executive Coaching und High Performance.",
        "--text", "-t"
    ),
    output: Path = typer.Option(Path("test_audio.mp3"), "--output", "-o"),
):
    """
    Testet die konfigurierte Stimme mit einem kurzen Text.
    """
    from src.voice import VoiceSynthesizer

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")

    if not api_key or not voice_id:
        console.print("[red]ELEVENLABS_API_KEY und ELEVENLABS_VOICE_ID müssen gesetzt sein![/red]")
        console.print("Nutze 'python cli.py voice-clone' um eine Stimme zu klonen")
        raise typer.Exit(1)

    # LIZENZPRÜFUNG: Warnung anzeigen (aber Test erlauben)
    checker = LicenseChecker(api_key=api_key)
    allowed, message = checker.verify_commercial_use()
    if not allowed:
        console.print(f"\n[yellow]{message}[/yellow]")
        console.print("[yellow]Test wird fortgesetzt - aber kommerzielle Nutzung ist nicht erlaubt![/yellow]\n")
    else:
        console.print(f"[green]{message}[/green]\n")

    console.print(f"Generiere Audio für: '{text[:50]}...'")

    synth = VoiceSynthesizer(api_key=api_key, voice_id=voice_id)

    try:
        segment = synth.synthesize(text, output_path=output)
        console.print(f"[green]Audio gespeichert: {output}[/green]")
        console.print(f"Geschätzte Dauer: {segment.duration_seconds:.1f} Sekunden")
        console.print(f"Zeichen verbraucht: {len(text)}")

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
        console.print("\n[bold]Anleitung:[/bold]")
        console.print("1. https://console.cloud.google.com öffnen")
        console.print("2. Neues Projekt erstellen (oder bestehendes wählen)")
        console.print("3. APIs & Services -> YouTube Data API v3 aktivieren")
        console.print("4. APIs & Services -> Credentials -> OAuth2 Client ID erstellen")
        console.print("5. Application type: Desktop App")
        console.print("6. JSON herunterladen als 'client_secrets.json'")
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
    console.print(Panel.fit(
        "[bold]YouTube Video Automation - Setup[/bold]\n\n"
        "Dieser Assistent hilft bei der Einrichtung.",
        border_style="green"
    ))

    env_content = []

    # Anthropic
    console.print("\n[bold]1. Anthropic Claude (für Skript-Optimierung)[/bold]")
    console.print("   API Key: https://console.anthropic.com/")
    api_key = typer.prompt("Anthropic API Key", hide_input=True)
    env_content.append(f"ANTHROPIC_API_KEY={api_key}")

    # ElevenLabs
    console.print("\n[bold]2. ElevenLabs Voice Cloning[/bold]")
    console.print("   API Key: https://elevenlabs.io/api")
    if typer.confirm("ElevenLabs konfigurieren?", default=True):
        el_key = typer.prompt("ElevenLabs API Key", hide_input=True)
        env_content.append(f"ELEVENLABS_API_KEY={el_key}")

        if typer.confirm("Hast du bereits eine Voice ID (geklonte Stimme)?"):
            voice_id = typer.prompt("Voice ID")
            env_content.append(f"ELEVENLABS_VOICE_ID={voice_id}")
        else:
            console.print("[yellow]Nutze später 'python cli.py voice-clone' um deine Stimme zu klonen[/yellow]")

    # YouTube
    console.print("\n[bold]3. YouTube Upload[/bold]")
    console.print("   Benötigt: client_secrets.json von Google Cloud Console")
    if typer.confirm("YouTube Upload konfigurieren?", default=True):
        if typer.confirm("Hast du die client_secrets.json bereits?"):
            path = typer.prompt("Pfad zur Datei", default="client_secrets.json")
            env_content.append(f"YOUTUBE_CLIENT_SECRETS_FILE={path}")
        else:
            console.print("[yellow]Folge der Anleitung in 'python cli.py youtube-auth'[/yellow]")

    # .env speichern
    env_path = Path(".env")
    if env_path.exists() and not typer.confirm("\n.env existiert bereits. Überschreiben?"):
        console.print("Setup abgebrochen")
        raise typer.Exit(0)

    with open(env_path, "w") as f:
        f.write("\n".join(env_content))

    console.print(f"\n[green]Konfiguration gespeichert in {env_path}[/green]")

    console.print("\n[bold]Nächste Schritte:[/bold]")
    console.print("1. python cli.py voice-clone   - Deine Stimme klonen (einmalig)")
    console.print("2. python cli.py youtube-auth  - YouTube authentifizieren")
    console.print("3. python cli.py from-notebooklm -t 'Thema' -f text.txt  - Video erstellen")


@app.command("info")
def info():
    """
    Zeigt Informationen über die aktuelle Konfiguration.
    """
    console.print("[bold]YouTube Video Automation - Status[/bold]\n")

    table = Table(title="Konfiguration")
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Info")

    # Anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        table.add_row("Anthropic Claude", "[green]✓ Konfiguriert[/green]", f"Key: {api_key[:12]}...")
    else:
        table.add_row("Anthropic Claude", "[red]✗ Fehlt[/red]", "ANTHROPIC_API_KEY setzen")

    # ElevenLabs
    el_key = os.getenv("ELEVENLABS_API_KEY")
    el_voice = os.getenv("ELEVENLABS_VOICE_ID")
    if el_key and el_voice:
        table.add_row("ElevenLabs Voice", "[green]✓ Konfiguriert[/green]", f"Voice: {el_voice[:12]}...")

        # Lizenzstatus prüfen
        try:
            checker = LicenseChecker(api_key=el_key)
            status = checker.check_subscription()
            if status.can_use_commercially:
                table.add_row(
                    "ElevenLabs Lizenz",
                    "[green]✓ Commercial License[/green]",
                    f"Plan: {status.tier}, Zeichen: {status.characters_remaining:,} übrig"
                )
            else:
                table.add_row(
                    "ElevenLabs Lizenz",
                    "[red]✗ Keine Commercial License[/red]",
                    f"Plan: {status.tier} - Upgrade auf Starter erforderlich!"
                )
        except Exception:
            table.add_row("ElevenLabs Lizenz", "[yellow]? Unbekannt[/yellow]", "Konnte Status nicht prüfen")
    elif el_key:
        table.add_row("ElevenLabs Voice", "[yellow]⚠ Teilweise[/yellow]", "Voice ID fehlt - voice-clone ausführen")
    else:
        table.add_row("ElevenLabs Voice", "[red]✗ Fehlt[/red]", "ELEVENLABS_API_KEY setzen")

    # YouTube
    yt_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
    yt_creds = Path("youtube_credentials.pickle")
    if Path(yt_secrets).exists() and yt_creds.exists():
        table.add_row("YouTube Upload", "[green]✓ Konfiguriert[/green]", "Bereit zum Upload")
    elif Path(yt_secrets).exists():
        table.add_row("YouTube Upload", "[yellow]⚠ Teilweise[/yellow]", "youtube-auth ausführen")
    else:
        table.add_row("YouTube Upload", "[red]✗ Fehlt[/red]", "client_secrets.json fehlt")

    console.print(table)

    console.print("\n[bold]Workflow:[/bold]")
    console.print("1. Quellen in NotebookLM hochladen")
    console.print("2. Zusammenfassung generieren lassen")
    console.print("3. Text kopieren")
    console.print("4. python cli.py from-notebooklm -t 'Thema' -f text.txt --video --upload")


@app.command("list-voices")
def list_voices():
    """
    Listet alle verfügbaren ElevenLabs-Stimmen auf.
    """
    from src.voice import VoiceSynthesizer

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

        for voice in voices:
            table.add_row(
                voice["voice_id"],
                voice["name"],
                voice.get("category", ""),
            )

        console.print(table)
        console.print(f"\nGesamt: {len(voices)} Stimmen")

    except Exception as e:
        console.print(f"[red]Fehler: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
