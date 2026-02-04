# YouTube Video Automation

Automatisierte Erstellung von YouTube-Videos mit NotebookLM + Anthropic Claude + ElevenLabs.

## Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   NotebookLM    │     │ Anthropic Claude│     │   ElevenLabs    │     │    YouTube      │
│                 │     │                 │     │                 │     │                 │
│ Quellen laden   │────▶│ Skript für      │────▶│ Deine Stimme    │────▶│ Automatischer   │
│ Zusammenfassung │     │ YouTube         │     │ (Voice Clone)   │     │ Upload          │
│ generieren      │     │ optimieren      │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
      MANUELL                  AUTOMATISCH            AUTOMATISCH            AUTOMATISCH
```

## Features

- **NotebookLM-Integration**: Nutze NotebookLM für Quellenverarbeitung (manuell)
- **Claude Skript-Optimierung**: Anthropic Claude strukturiert für YouTube
- **Voice Cloning**: Deine eigene Stimme (einmalig klonen, dann automatisch)
- **Video-Generierung**: Automatische Erstellung mit Text-Overlays
- **YouTube-Upload**: Direkter Upload mit Metadaten, Timestamps, Tags

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
python cli.py setup
```

### 3. Stimme klonen (EINMALIG)

```bash
# Audio-Samples vorbereiten (mind. 1-3 Minuten)
python cli.py voice-clone --name "Katja" --sample audio1.mp3 --sample audio2.mp3
```

### 4. Video erstellen

```bash
# 1. Quellen in NotebookLM hochladen
# 2. Zusammenfassung generieren
# 3. Text in eine Datei kopieren (z.B. notebooklm_output.txt)
# 4. Pipeline ausführen:

python cli.py full-pipeline -t "Stressmanagement" -f notebooklm_output.txt
```

## CLI-Befehle

| Befehl | Beschreibung |
|--------|-------------|
| `from-notebooklm` | NotebookLM-Text zu YouTube-Skript |
| `full-pipeline` | Komplette Pipeline (Skript → Audio → Video → YouTube) |
| `voice-clone` | Stimme aus Audio-Samples klonen (einmalig) |
| `test-voice` | Konfigurierte Stimme testen |
| `youtube-auth` | YouTube-Authentifizierung |
| `setup` | Interaktiver Setup-Assistent |
| `info` | Status der Konfiguration |
| `list-voices` | Verfügbare ElevenLabs-Stimmen |

## Beispiele

### Nur Skript generieren (ohne Video)

```bash
python cli.py from-notebooklm \
  --topic "Breathwork für Führungskräfte" \
  --file notebooklm_output.txt \
  --duration 10
```

### Komplette Pipeline mit Upload

```bash
python cli.py full-pipeline \
  --topic "Breathwork für Führungskräfte" \
  --file notebooklm_output.txt \
  --privacy unlisted
```

### Skript + Video ohne Upload

```bash
python cli.py from-notebooklm \
  --topic "Breathwork" \
  --file text.txt \
  --video
```

## API-Keys einrichten

### 1. Anthropic Claude (für Skript-Optimierung)

1. https://console.anthropic.com/
2. API Key erstellen
3. In `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### 2. ElevenLabs (für Voice Cloning)

1. https://elevenlabs.io registrieren
2. API Key unter https://elevenlabs.io/api kopieren
3. In `.env`: `ELEVENLABS_API_KEY=...`
4. Stimme klonen: `python cli.py voice-clone`
5. Voice ID in `.env`: `ELEVENLABS_VOICE_ID=...`

### 3. YouTube Data API

1. https://console.cloud.google.com
2. Neues Projekt erstellen
3. YouTube Data API v3 aktivieren
4. OAuth2 Client ID erstellen (Desktop App)
5. JSON herunterladen als `client_secrets.json`
6. `python cli.py youtube-auth` ausführen

## Kosten

### Voice Cloning (ElevenLabs)

| Aktion | Kosten |
|--------|--------|
| Stimme klonen | EINMALIG, kostenlos |
| Nutzung | Nach Zeichen/Monat |

| Plan | Zeichen/Monat | Videos (~10 Min) | Preis |
|------|---------------|------------------|-------|
| Free | 10.000 | ~1 | $0 |
| Starter | 30.000 | ~3 | $5/Mo |
| Creator | 100.000 | ~10 | $22/Mo |
| Pro | 500.000 | ~50 | $99/Mo |

### Anthropic Claude

- Ca. $0.01-0.05 pro Skript-Optimierung
- Sehr günstig im Vergleich zu ElevenLabs

### YouTube API

- Kostenlos (Limits beachten)

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

## Projektstruktur

```
youtube-automation/
├── cli.py                    # Kommandozeilen-Interface
├── requirements.txt          # Python-Abhängigkeiten
├── .env.example              # Beispiel-Konfiguration
├── config/
│   └── settings.py           # Zentrale Einstellungen
├── src/
│   ├── script_gen/           # Skript-Generierung (Claude)
│   │   └── script_generator.py
│   ├── voice/                # Voice Synthesis (ElevenLabs)
│   │   └── voice_synthesizer.py
│   ├── video/                # Video-Erstellung
│   │   └── video_generator.py
│   ├── upload/               # YouTube-Upload
│   │   └── youtube_uploader.py
│   └── sources/              # Optional: Direkte Quellenverarbeitung
└── data/
    ├── scripts/              # Generierte Skripte
    ├── audio/                # Audio-Dateien
    └── videos/               # Fertige Videos
```

## Troubleshooting

### "ELEVENLABS_VOICE_ID nicht gesetzt"
Führe zuerst `python cli.py voice-clone` aus.

### "YouTube Upload fehlgeschlagen"
1. Prüfe ob `client_secrets.json` existiert
2. Führe `python cli.py youtube-auth` aus
3. Prüfe API-Limits in Google Cloud Console

### "Kein Audio generiert"
ElevenLabs API Key und Voice ID in `.env` prüfen.

### "Anthropic API Fehler"
ANTHROPIC_API_KEY in `.env` prüfen.

## Lizenz

Privates Projekt für Katja Kaiser Coaching.
