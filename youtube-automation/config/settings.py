"""
Zentrale Konfiguration für das YouTube-Automatisierungssystem.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Hauptkonfiguration - Werte werden aus .env geladen."""

    # === Basis-Pfade ===
    base_dir: Path = Field(default=Path(__file__).parent.parent)
    data_dir: Path = Field(default=None)

    # === Anthropic Claude API ===
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")

    # LLM Einstellungen (nur Anthropic Claude)
    llm_model: str = Field(default="claude-sonnet-4-20250514", alias="LLM_MODEL")

    # === ElevenLabs Voice Cloning ===
    elevenlabs_api_key: Optional[str] = Field(default=None, alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: Optional[str] = Field(default=None, alias="ELEVENLABS_VOICE_ID")

    # Voice Settings
    voice_stability: float = Field(default=0.5, alias="VOICE_STABILITY")
    voice_similarity_boost: float = Field(default=0.75, alias="VOICE_SIMILARITY_BOOST")
    voice_style: float = Field(default=0.0, alias="VOICE_STYLE")

    # === YouTube API ===
    youtube_client_secrets_file: Optional[str] = Field(
        default=None,
        alias="YOUTUBE_CLIENT_SECRETS_FILE"
    )
    youtube_credentials_file: Optional[str] = Field(
        default="youtube_credentials.json",
        alias="YOUTUBE_CREDENTIALS_FILE"
    )

    # YouTube Default Settings
    youtube_category_id: str = Field(default="22", alias="YOUTUBE_CATEGORY_ID")  # 22 = People & Blogs
    youtube_privacy_status: str = Field(default="private", alias="YOUTUBE_PRIVACY_STATUS")
    youtube_default_language: str = Field(default="de", alias="YOUTUBE_DEFAULT_LANGUAGE")

    # === Video Generation ===
    video_width: int = Field(default=1920, alias="VIDEO_WIDTH")
    video_height: int = Field(default=1080, alias="VIDEO_HEIGHT")
    video_fps: int = Field(default=30, alias="VIDEO_FPS")

    # Pexels API für Stock Videos (optional)
    pexels_api_key: Optional[str] = Field(default=None, alias="PEXELS_API_KEY")

    # === Skript-Generierung ===
    default_video_length_minutes: int = Field(default=10, alias="DEFAULT_VIDEO_LENGTH_MINUTES")
    default_language: str = Field(default="de", alias="DEFAULT_LANGUAGE")

    # Brand Settings für Katja Kaiser
    brand_name: str = Field(default="Katja Kaiser Coaching", alias="BRAND_NAME")
    brand_tagline: str = Field(
        default="Executive Performance, Leadership & Breathwork",
        alias="BRAND_TAGLINE"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"


# Globale Settings-Instanz
settings = Settings()


# Prompt Templates
SCRIPT_SYSTEM_PROMPT = """Du bist ein erfahrener Skriptautor für YouTube-Videos im Bereich
Executive Coaching, Leadership und persönliche Entwicklung.

Dein Stil ist:
- Professionell aber nahbar
- Wissenschaftlich fundiert aber verständlich
- Inspirierend und motivierend
- Strukturiert mit klaren Takeaways

Der Sprecher ist Katja Kaiser, eine Executive Coach mit Expertise in:
- Executive Performance
- Leadership Development
- Breathwork & Stressmanagement
- Mindset & Selbstführung

Erstelle Skripte, die:
1. Mit einem Hook beginnen, der sofort Aufmerksamkeit erregt
2. Das Problem/Thema klar definieren
3. Wissenschaftliche Erkenntnisse einbinden
4. Praktische Übungen oder Tipps geben
5. Mit einem klaren Call-to-Action enden
"""

VIDEO_DESCRIPTION_TEMPLATE = """
{title}

{summary}

📚 In diesem Video lernst du:
{key_points}

🔗 Quellen & Weiterführende Links:
{sources}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 Kontakt: kontakt@katjakaiser-coaching.de
🌐 Website: https://katjakaiser-coaching.de

#ExecutiveCoaching #Leadership #Performance #KatjaKaiser
"""
