# YouTube Video Automation

Automatisierte Erstellung von YouTube-Videos aus PDFs, Webseiten und anderen Quellen.

## Features

- **Quellenverarbeitung**: PDFs, URLs, wissenschaftliche Studien
- **KI-Skript-Generierung**: OpenAI GPT-4 oder Anthropic Claude
- **Voice Cloning**: ElevenLabs für personalisierte Stimme
- **Video-Generierung**: Automatische Erstellung mit Text-Overlays
- **YouTube-Upload**: Direkter Upload mit Metadaten

## Schnellstart

### 1. Installation

```bash
cd youtube-automation
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Konfiguration

```bash
# Interaktiver Setup
python cli.py setup

# Oder manuell: .env.example nach .env kopieren und ausfüllen
cp .env.example .env
```

### 3. Stimme klonen (einmalig)

```bash
# Audio-Samples vorbereiten (mind. 1-3 Minuten)
python cli.py voice-clone --name "Katja" --sample audio1.mp3 --sample audio2.mp3
```

### 4. Video erstellen

```bash
python cli.py create \
  --topic "Stressmanagement für Führungskräfte" \
  --pdf studie.pdf \
  --url https://example.com/artikel \
  --duration 10 \
  --upload
```

## Projektstruktur

```
youtube-automation/
├── cli.py                    # Kommandozeilen-Interface
├── requirements.txt          # Python-Abhängigkeiten
├── .env.example              # Beispiel-Konfiguration
├── config/
│   └── settings.py           # Zentrale Einstellungen
├── src/
│   ├── pipeline.py           # Haupt-Pipeline
│   ├── sources/              # Quellenverarbeitung
│   │   ├── pdf_processor.py
│   │   ├── web_processor.py
│   │   └── source_manager.py
│   ├── script_gen/           # Skript-Generierung
│   │   └── script_generator.py
│   ├── voice/                # Voice Synthesis
│   │   └── voice_synthesizer.py
│   ├── video/                # Video-Erstellung
│   │   └── video_generator.py
│   └── upload/               # YouTube-Upload
│       └── youtube_uploader.py
└── data/                     # Generierte Dateien
    ├── sources/              # Quellensammlungen
    ├── scripts/              # Generierte Skripte
    ├── audio/                # Audio-Dateien
    └── videos/               # Fertige Videos
```

## CLI-Befehle

| Befehl | Beschreibung |
|--------|-------------|
| `create` | Video aus Quellen erstellen |
| `voice-clone` | Stimme aus Audio-Samples klonen |
| `list-voices` | Verfügbare ElevenLabs-Stimmen |
| `test-voice` | Konfigurierte Stimme testen |
| `youtube-auth` | YouTube-Authentifizierung |
| `setup` | Interaktiver Setup-Assistent |
| `info` | Aktuelle Konfiguration anzeigen |

## API-Keys einrichten

### OpenAI oder Anthropic (für Skript-Generierung)

**OpenAI:**
1. https://platform.openai.com/api-keys
2. API Key erstellen
3. In `.env`: `OPENAI_API_KEY=sk-...`

**Anthropic:**
1. https://console.anthropic.com/
2. API Key erstellen
3. In `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### ElevenLabs (für Voice Cloning)

1. https://elevenlabs.io registrieren
2. API Key unter https://elevenlabs.io/api kopieren
3. In `.env`: `ELEVENLABS_API_KEY=...`
4. Stimme klonen mit `python cli.py voice-clone`
5. Voice ID in `.env`: `ELEVENLABS_VOICE_ID=...`

### YouTube Data API

1. https://console.cloud.google.com
2. Neues Projekt erstellen
3. YouTube Data API v3 aktivieren
4. OAuth2 Client ID erstellen (Desktop App)
5. JSON herunterladen als `client_secrets.json`
6. `python cli.py youtube-auth` ausführen

## Python-API verwenden

```python
from src.pipeline import VideoPipeline, PipelineConfig

# Pipeline konfigurieren
config = PipelineConfig(
    llm_provider="openai",
    llm_api_key="sk-...",
    elevenlabs_api_key="...",
    elevenlabs_voice_id="...",
)

pipeline = VideoPipeline(config)

# Quellen hinzufügen
pipeline.add_pdf("studie.pdf")
pipeline.add_url("https://example.com/artikel")

# Video erstellen
result = pipeline.run(
    topic="Stressmanagement für Führungskräfte",
    target_duration_minutes=10,
    upload_to_youtube=True
)

if result.success:
    print(f"Video: {result.video_path}")
    print(f"YouTube: {result.youtube_result.video_url}")
```

## Audio-Samples für Voice Cloning

Für beste Ergebnisse:

- **Länge**: 1-3 Minuten (mehr = besser)
- **Qualität**: Mindestens 44.1kHz, 16-bit
- **Format**: MP3, WAV, M4A
- **Umgebung**: Ruhig, ohne Hintergrundgeräusche
- **Inhalt**: Natürliche Sprache, verschiedene Sätze

**Beispiel-Skript zum Einsprechen:**

> "Hallo, ich bin Katja. Heute möchte ich über ein wichtiges Thema sprechen.
> Wussten Sie, dass Atmung einen enormen Einfluss auf unsere Leistungsfähigkeit hat?
> Das klingt vielleicht überraschend, aber es stimmt tatsächlich.
> Lassen Sie mich Ihnen erklären, wie das funktioniert.
> Fragen Sie sich manchmal, warum manche Tage besser laufen als andere?
> Die Antwort könnte einfacher sein, als Sie denken!"

## Kosten-Übersicht

| Service | Kosten | Hinweis |
|---------|--------|---------|
| OpenAI GPT-4 | ~$0.03/1K Tokens | Ca. $0.50-1.00 pro Skript |
| ElevenLabs | Ab $5/Monat | 30.000 Zeichen/Monat |
| YouTube API | Kostenlos | Limits beachten |

## Workflow ohne NotebookLM

Da NotebookLM keine offizielle API hat, nutzt dieses System:

1. **LangChain/OpenAI** für Quellenverarbeitung und Zusammenfassung
2. **Eigenes RAG-System** (optional mit ChromaDB)

Du kannst NotebookLM parallel manuell nutzen:
1. Quellen in NotebookLM hochladen
2. Zusammenfassung/Podcast generieren
3. Text kopieren und als Quelle hier verwenden

## Troubleshooting

### "ELEVENLABS_VOICE_ID nicht gesetzt"
Führe zuerst `python cli.py voice-clone` aus.

### "YouTube Upload fehlgeschlagen"
1. Prüfe ob `client_secrets.json` existiert
2. Führe `python cli.py youtube-auth` aus
3. Prüfe API-Limits in Google Cloud Console

### "Kein Audio generiert"
ElevenLabs API Key und Voice ID in `.env` prüfen.

## Lizenz

Privates Projekt für Katja Kaiser Coaching.
