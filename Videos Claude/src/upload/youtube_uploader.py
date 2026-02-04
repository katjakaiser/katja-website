"""
YouTube Upload mit der YouTube Data API v3.

Automatisiert den Upload von Videos zu YouTube inkl. Metadaten.
"""

import json
import logging
import os
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# OAuth2 Scopes für YouTube
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


@dataclass
class VideoMetadata:
    """Metadaten für ein YouTube-Video."""

    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    category_id: str = "22"  # 22 = People & Blogs
    privacy_status: Literal["private", "unlisted", "public"] = "private"
    language: str = "de"

    # Optionale Felder
    thumbnail_path: Optional[Path] = None
    playlist_id: Optional[str] = None
    scheduled_publish_time: Optional[datetime] = None

    # YouTube-spezifisch
    made_for_kids: bool = False
    embeddable: bool = True
    public_stats_viewable: bool = True

    def to_youtube_body(self) -> dict:
        """Konvertiert zu YouTube API Body-Format."""
        body = {
            "snippet": {
                "title": self.title[:100],  # Max 100 Zeichen
                "description": self.description[:5000],  # Max 5000 Zeichen
                "tags": self.tags[:500],  # Max 500 Tags
                "categoryId": self.category_id,
                "defaultLanguage": self.language,
                "defaultAudioLanguage": self.language,
            },
            "status": {
                "privacyStatus": self.privacy_status,
                "selfDeclaredMadeForKids": self.made_for_kids,
                "embeddable": self.embeddable,
                "publicStatsViewable": self.public_stats_viewable,
            },
        }

        # Geplante Veröffentlichung
        if self.scheduled_publish_time and self.privacy_status == "private":
            body["status"]["publishAt"] = self.scheduled_publish_time.isoformat() + "Z"
            body["status"]["privacyStatus"] = "private"

        return body


@dataclass
class UploadResult:
    """Ergebnis eines Video-Uploads."""

    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    upload_time: datetime = field(default_factory=datetime.now)

    @property
    def youtube_studio_url(self) -> Optional[str]:
        """URL zum Video in YouTube Studio."""
        if self.video_id:
            return f"https://studio.youtube.com/video/{self.video_id}/edit"
        return None


class YouTubeUploader:
    """
    Lädt Videos zu YouTube hoch.

    Setup:
    1. Google Cloud Console: YouTube Data API v3 aktivieren
    2. OAuth2 Client ID erstellen (Desktop App)
    3. client_secrets.json herunterladen

    Beispiel:
        uploader = YouTubeUploader(
            client_secrets_file="client_secrets.json"
        )

        # Authentifizieren (öffnet Browser beim ersten Mal)
        uploader.authenticate()

        # Video hochladen
        result = uploader.upload(
            video_path="video.mp4",
            metadata=VideoMetadata(
                title="Mein Video",
                description="Beschreibung...",
                tags=["coaching", "leadership"],
            )
        )

        print(f"Video-URL: {result.video_url}")
    """

    def __init__(
        self,
        client_secrets_file: Path | str,
        credentials_file: Optional[Path | str] = None,
    ):
        self.client_secrets_file = Path(client_secrets_file)
        self.credentials_file = Path(credentials_file or "youtube_credentials.pickle")

        self._youtube = None
        self._credentials = None

    def authenticate(self) -> bool:
        """
        Authentifiziert den Benutzer bei YouTube.

        Beim ersten Aufruf wird ein Browser geöffnet zur Autorisierung.
        Danach werden die Credentials lokal gespeichert.

        Returns:
            True wenn erfolgreich authentifiziert
        """
        # Versuche gespeicherte Credentials zu laden
        if self.credentials_file.exists():
            with open(self.credentials_file, "rb") as f:
                self._credentials = pickle.load(f)

        # Credentials prüfen/erneuern
        if self._credentials:
            if self._credentials.expired and self._credentials.refresh_token:
                logger.info("Erneuere abgelaufene Credentials...")
                self._credentials.refresh(Request())
            elif not self._credentials.valid:
                self._credentials = None

        # Neue Authentifizierung wenn nötig
        if not self._credentials:
            if not self.client_secrets_file.exists():
                raise FileNotFoundError(
                    f"client_secrets.json nicht gefunden: {self.client_secrets_file}\n"
                    "Bitte von Google Cloud Console herunterladen."
                )

            logger.info("Starte OAuth2-Authentifizierung...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_file),
                SCOPES,
            )
            self._credentials = flow.run_local_server(port=8080)

            # Credentials speichern
            with open(self.credentials_file, "wb") as f:
                pickle.dump(self._credentials, f)
            logger.info(f"Credentials gespeichert: {self.credentials_file}")

        # YouTube Service erstellen
        self._youtube = build("youtube", "v3", credentials=self._credentials)
        logger.info("YouTube API authentifiziert")

        return True

    def upload(
        self,
        video_path: Path | str,
        metadata: VideoMetadata,
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ) -> UploadResult:
        """
        Lädt ein Video zu YouTube hoch.

        Args:
            video_path: Pfad zur Video-Datei
            metadata: Video-Metadaten
            chunk_size: Upload-Chunk-Größe

        Returns:
            UploadResult mit Video-ID und URL
        """
        if not self._youtube:
            raise RuntimeError("Nicht authentifiziert. Bitte zuerst authenticate() aufrufen.")

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video nicht gefunden: {video_path}")

        logger.info(f"Starte Upload: {video_path.name}")
        logger.info(f"Titel: {metadata.title}")

        try:
            # Upload-Request erstellen
            body = metadata.to_youtube_body()

            media = MediaFileUpload(
                str(video_path),
                mimetype="video/*",
                resumable=True,
                chunksize=chunk_size,
            )

            request = self._youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            # Upload durchführen (mit Fortschrittsanzeige)
            response = self._execute_upload(request)

            video_id = response["id"]
            logger.info(f"Upload erfolgreich! Video-ID: {video_id}")

            # Thumbnail setzen wenn vorhanden
            if metadata.thumbnail_path and metadata.thumbnail_path.exists():
                self._set_thumbnail(video_id, metadata.thumbnail_path)

            # Zur Playlist hinzufügen wenn angegeben
            if metadata.playlist_id:
                self._add_to_playlist(video_id, metadata.playlist_id)

            return UploadResult(
                success=True,
                video_id=video_id,
                video_url=f"https://www.youtube.com/watch?v={video_id}",
            )

        except HttpError as e:
            error_msg = f"YouTube API Fehler: {e.resp.status} - {e.content}"
            logger.error(error_msg)
            return UploadResult(
                success=False,
                error_message=error_msg,
            )

        except Exception as e:
            error_msg = f"Upload fehlgeschlagen: {str(e)}"
            logger.error(error_msg)
            return UploadResult(
                success=False,
                error_message=error_msg,
            )

    def _execute_upload(self, request) -> dict:
        """Führt den Upload mit Fortschrittsanzeige durch."""
        response = None
        retry_count = 0
        max_retries = 3

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload-Fortschritt: {progress}%")

            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    retry_count += 1
                    if retry_count > max_retries:
                        raise
                    logger.warning(f"Upload-Fehler, Retry {retry_count}/{max_retries}...")
                    import time

                    time.sleep(2 ** retry_count)
                else:
                    raise

        return response

    def _set_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """Setzt das Video-Thumbnail."""
        try:
            self._youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path)),
            ).execute()
            logger.info(f"Thumbnail gesetzt für Video {video_id}")
            return True
        except HttpError as e:
            logger.warning(f"Thumbnail setzen fehlgeschlagen: {e}")
            return False

    def _add_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        """Fügt das Video zu einer Playlist hinzu."""
        try:
            self._youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    },
                },
            ).execute()
            logger.info(f"Video {video_id} zu Playlist {playlist_id} hinzugefügt")
            return True
        except HttpError as e:
            logger.warning(f"Playlist-Hinzufügen fehlgeschlagen: {e}")
            return False

    def update_video(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        privacy_status: Optional[str] = None,
    ) -> bool:
        """
        Aktualisiert die Metadaten eines bestehenden Videos.

        Args:
            video_id: YouTube Video-ID
            title: Neuer Titel
            description: Neue Beschreibung
            tags: Neue Tags
            privacy_status: Neuer Datenschutz-Status

        Returns:
            True wenn erfolgreich
        """
        if not self._youtube:
            raise RuntimeError("Nicht authentifiziert.")

        try:
            # Aktuelle Video-Daten abrufen
            video = (
                self._youtube.videos()
                .list(part="snippet,status", id=video_id)
                .execute()
            )

            if not video["items"]:
                raise ValueError(f"Video nicht gefunden: {video_id}")

            snippet = video["items"][0]["snippet"]
            status = video["items"][0]["status"]

            # Updates anwenden
            if title:
                snippet["title"] = title
            if description:
                snippet["description"] = description
            if tags:
                snippet["tags"] = tags
            if privacy_status:
                status["privacyStatus"] = privacy_status

            # Update durchführen
            self._youtube.videos().update(
                part="snippet,status",
                body={
                    "id": video_id,
                    "snippet": snippet,
                    "status": status,
                },
            ).execute()

            logger.info(f"Video {video_id} aktualisiert")
            return True

        except HttpError as e:
            logger.error(f"Update fehlgeschlagen: {e}")
            return False

    def get_channel_info(self) -> dict:
        """Gibt Informationen über den authentifizierten Kanal zurück."""
        if not self._youtube:
            raise RuntimeError("Nicht authentifiziert.")

        response = (
            self._youtube.channels()
            .list(part="snippet,statistics", mine=True)
            .execute()
        )

        if response["items"]:
            channel = response["items"][0]
            return {
                "id": channel["id"],
                "title": channel["snippet"]["title"],
                "description": channel["snippet"]["description"],
                "subscriber_count": channel["statistics"].get("subscriberCount"),
                "video_count": channel["statistics"].get("videoCount"),
                "view_count": channel["statistics"].get("viewCount"),
            }
        return {}

    def list_playlists(self) -> list[dict]:
        """Listet alle Playlists des Kanals auf."""
        if not self._youtube:
            raise RuntimeError("Nicht authentifiziert.")

        response = (
            self._youtube.playlists()
            .list(part="snippet", mine=True, maxResults=50)
            .execute()
        )

        return [
            {
                "id": pl["id"],
                "title": pl["snippet"]["title"],
                "description": pl["snippet"]["description"],
            }
            for pl in response.get("items", [])
        ]


class YouTubeScheduler:
    """
    Hilfsfunktionen für geplante Veröffentlichungen.
    """

    @staticmethod
    def schedule_for_optimal_time(
        base_date: datetime,
        target_audience: Literal["business", "general"] = "business",
    ) -> datetime:
        """
        Berechnet optimale Veröffentlichungszeit.

        Für Business-Audience: Dienstag-Donnerstag, 9-11 Uhr
        Für Allgemein: Samstag-Sonntag, 14-18 Uhr

        Args:
            base_date: Frühestes Veröffentlichungsdatum
            target_audience: Zielgruppe

        Returns:
            Optimaler Veröffentlichungszeitpunkt
        """
        from datetime import timedelta

        if target_audience == "business":
            # Nächsten Dienstag, Mittwoch oder Donnerstag finden
            while base_date.weekday() not in [1, 2, 3]:  # Di, Mi, Do
                base_date += timedelta(days=1)
            # 10:00 Uhr
            return base_date.replace(hour=10, minute=0, second=0, microsecond=0)
        else:
            # Nächsten Samstag oder Sonntag finden
            while base_date.weekday() not in [5, 6]:  # Sa, So
                base_date += timedelta(days=1)
            # 15:00 Uhr
            return base_date.replace(hour=15, minute=0, second=0, microsecond=0)
