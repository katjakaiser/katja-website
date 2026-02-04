"""
Video-Generierung mit MoviePy.

Erstellt Videos aus Audio und visuellen Elementen.
"""

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VideoConfig:
    """Konfiguration für die Video-Generierung."""

    width: int = 1920
    height: int = 1080
    fps: int = 30

    # Farben (RGB)
    background_color: tuple = (15, 15, 20)  # Dunkler Hintergrund
    accent_color: tuple = (212, 175, 55)  # Gold (#D4AF37)
    text_color: tuple = (255, 255, 255)  # Weiß

    # Fonts
    title_font: str = "Arial-Bold"
    body_font: str = "Arial"
    title_font_size: int = 72
    body_font_size: int = 48

    # Branding
    logo_path: Optional[Path] = None
    watermark_text: str = "Katja Kaiser Coaching"

    # Output
    output_format: Literal["mp4", "webm"] = "mp4"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    bitrate: str = "8000k"


@dataclass
class VideoScene:
    """Eine Szene im Video."""

    duration: float  # Dauer in Sekunden
    background: Optional[str] = None  # Pfad zu Bild/Video oder Farbe
    title: Optional[str] = None
    subtitle: Optional[str] = None
    text_overlay: Optional[str] = None
    animation: Literal["fade", "slide", "zoom", "none"] = "fade"


class VideoGenerator:
    """
    Generiert Videos aus Audio und visuellen Elementen.

    Beispiel:
        generator = VideoGenerator()

        # Einfaches Video mit Audio
        video = generator.create_simple_video(
            audio_path="narration.mp3",
            title="Mein Video",
            output_path="output.mp4"
        )

        # Video mit Szenen
        scenes = [
            VideoScene(duration=5, title="Einführung"),
            VideoScene(duration=30, text_overlay="Wichtiger Punkt"),
            VideoScene(duration=10, title="Fazit"),
        ]
        video = generator.create_video_with_scenes(
            audio_path="narration.mp3",
            scenes=scenes,
            output_path="output.mp4"
        )
    """

    def __init__(
        self,
        config: Optional[VideoConfig] = None,
        output_dir: Optional[Path | str] = None,
    ):
        self.config = config or VideoConfig()
        self.output_dir = Path(output_dir) if output_dir else Path("./data/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_simple_video(
        self,
        audio_path: Path | str,
        title: str,
        subtitle: str = "",
        output_path: Optional[Path | str] = None,
        background_image: Optional[Path | str] = None,
    ) -> Path:
        """
        Erstellt ein einfaches Video mit Titel und Audio.

        Args:
            audio_path: Pfad zur Audio-Datei
            title: Video-Titel
            subtitle: Optionaler Untertitel
            output_path: Ausgabepfad
            background_image: Optionales Hintergrundbild

        Returns:
            Pfad zum generierten Video
        """
        logger.info(f"Erstelle Video: {title}")

        audio = AudioFileClip(str(audio_path))
        duration = audio.duration

        # Hintergrund erstellen
        if background_image:
            bg = self._create_image_background(background_image, duration)
        else:
            bg = self._create_gradient_background(duration)

        # Text-Overlays erstellen
        clips = [bg]

        # Titel
        title_clip = self._create_text_clip(
            title,
            font_size=self.config.title_font_size,
            font=self.config.title_font,
            color=self.config.accent_color,
        ).set_position(("center", 0.35), relative=True).set_duration(duration)
        clips.append(title_clip)

        # Untertitel
        if subtitle:
            subtitle_clip = self._create_text_clip(
                subtitle,
                font_size=self.config.body_font_size,
                color=self.config.text_color,
            ).set_position(("center", 0.45), relative=True).set_duration(duration)
            clips.append(subtitle_clip)

        # Watermark
        watermark = self._create_watermark().set_duration(duration)
        clips.append(watermark)

        # Video zusammensetzen
        video = CompositeVideoClip(clips, size=(self.config.width, self.config.height))
        video = video.set_audio(audio)

        # Speichern
        if not output_path:
            output_path = self.output_dir / f"{self._safe_filename(title)}.{self.config.output_format}"

        video.write_videofile(
            str(output_path),
            fps=self.config.fps,
            codec=self.config.video_codec,
            audio_codec=self.config.audio_codec,
            bitrate=self.config.bitrate,
            logger=None,  # MoviePy Logging unterdrücken
        )

        # Aufräumen
        audio.close()
        video.close()

        logger.info(f"Video gespeichert: {output_path}")
        return Path(output_path)

    def create_video_with_scenes(
        self,
        audio_path: Path | str,
        scenes: list[VideoScene],
        output_path: Optional[Path | str] = None,
    ) -> Path:
        """
        Erstellt ein Video mit mehreren Szenen.

        Args:
            audio_path: Pfad zur Audio-Datei
            scenes: Liste von VideoScene-Objekten
            output_path: Ausgabepfad

        Returns:
            Pfad zum generierten Video
        """
        logger.info(f"Erstelle Video mit {len(scenes)} Szenen")

        audio = AudioFileClip(str(audio_path))

        # Szenen erstellen
        scene_clips = []
        for i, scene in enumerate(scenes):
            logger.info(f"Erstelle Szene {i + 1}/{len(scenes)}")
            clip = self._create_scene(scene)
            scene_clips.append(clip)

        # Szenen verbinden
        video = concatenate_videoclips(scene_clips, method="compose")

        # Audio hinzufügen (auf Video-Länge trimmen)
        if video.duration < audio.duration:
            audio = audio.subclip(0, video.duration)
        video = video.set_audio(audio)

        # Speichern
        if not output_path:
            output_path = self.output_dir / f"video_{len(scenes)}_scenes.{self.config.output_format}"

        video.write_videofile(
            str(output_path),
            fps=self.config.fps,
            codec=self.config.video_codec,
            audio_codec=self.config.audio_codec,
            bitrate=self.config.bitrate,
            logger=None,
        )

        # Aufräumen
        audio.close()
        video.close()
        for clip in scene_clips:
            clip.close()

        logger.info(f"Video gespeichert: {output_path}")
        return Path(output_path)

    def create_video_with_key_points(
        self,
        audio_path: Path | str,
        title: str,
        key_points: list[str],
        output_path: Optional[Path | str] = None,
    ) -> Path:
        """
        Erstellt ein Video das Key Points nacheinander einblendet.

        Args:
            audio_path: Pfad zur Audio-Datei
            title: Video-Titel
            key_points: Liste von Schlüsselpunkten
            output_path: Ausgabepfad

        Returns:
            Pfad zum generierten Video
        """
        audio = AudioFileClip(str(audio_path))
        duration = audio.duration

        # Zeit pro Punkt berechnen (mit Intro und Outro)
        intro_duration = min(10, duration * 0.1)
        outro_duration = min(10, duration * 0.1)
        content_duration = duration - intro_duration - outro_duration
        point_duration = content_duration / len(key_points) if key_points else content_duration

        # Clips erstellen
        clips = []

        # Intro
        intro = self._create_scene(VideoScene(
            duration=intro_duration,
            title=title,
            animation="fade",
        ))
        clips.append(intro)

        # Key Points
        for point in key_points:
            point_clip = self._create_scene(VideoScene(
                duration=point_duration,
                text_overlay=point,
                animation="slide",
            ))
            clips.append(point_clip)

        # Outro
        outro = self._create_scene(VideoScene(
            duration=outro_duration,
            title="Vielen Dank!",
            subtitle=self.config.watermark_text,
            animation="fade",
        ))
        clips.append(outro)

        # Zusammenfügen
        video = concatenate_videoclips(clips, method="compose")
        video = video.set_audio(audio)

        if not output_path:
            output_path = self.output_dir / f"{self._safe_filename(title)}.{self.config.output_format}"

        video.write_videofile(
            str(output_path),
            fps=self.config.fps,
            codec=self.config.video_codec,
            audio_codec=self.config.audio_codec,
            bitrate=self.config.bitrate,
            logger=None,
        )

        audio.close()
        video.close()

        return Path(output_path)

    def _create_scene(self, scene: VideoScene) -> CompositeVideoClip:
        """Erstellt einen Clip für eine Szene."""
        clips = []

        # Hintergrund
        if scene.background:
            if Path(scene.background).exists():
                bg = self._create_image_background(scene.background, scene.duration)
            else:
                bg = self._create_gradient_background(scene.duration)
        else:
            bg = self._create_gradient_background(scene.duration)
        clips.append(bg)

        # Titel
        if scene.title:
            title_clip = self._create_text_clip(
                scene.title,
                font_size=self.config.title_font_size,
                font=self.config.title_font,
                color=self.config.accent_color,
            ).set_position(("center", 0.35), relative=True).set_duration(scene.duration)

            # Animation
            if scene.animation == "fade":
                title_clip = title_clip.crossfadein(0.5).crossfadeout(0.5)

            clips.append(title_clip)

        # Untertitel
        if scene.subtitle:
            subtitle_clip = self._create_text_clip(
                scene.subtitle,
                font_size=self.config.body_font_size,
                color=self.config.text_color,
            ).set_position(("center", 0.45), relative=True).set_duration(scene.duration)
            clips.append(subtitle_clip)

        # Text Overlay
        if scene.text_overlay:
            text_clip = self._create_text_clip(
                scene.text_overlay,
                font_size=self.config.body_font_size,
                color=self.config.text_color,
                max_width=self.config.width - 200,
            ).set_position(("center", "center")).set_duration(scene.duration)

            if scene.animation == "fade":
                text_clip = text_clip.crossfadein(0.5).crossfadeout(0.5)

            clips.append(text_clip)

        # Watermark
        watermark = self._create_watermark().set_duration(scene.duration)
        clips.append(watermark)

        return CompositeVideoClip(clips, size=(self.config.width, self.config.height))

    def _create_gradient_background(self, duration: float) -> ColorClip:
        """Erstellt einen Gradient-Hintergrund."""
        # Für MoviePy verwenden wir erstmal einen einfachen Farbhintergrund
        # TODO: Echten Gradient mit numpy implementieren
        return ColorClip(
            size=(self.config.width, self.config.height),
            color=self.config.background_color,
            duration=duration,
        )

    def _create_image_background(self, image_path: Path | str, duration: float) -> ImageClip:
        """Erstellt einen Hintergrund aus einem Bild."""
        img = ImageClip(str(image_path))

        # Auf Video-Größe skalieren
        img = img.resize(height=self.config.height)
        if img.w < self.config.width:
            img = img.resize(width=self.config.width)

        # Zentrieren und zuschneiden
        img = img.set_position("center")
        img = img.set_duration(duration)

        return img

    def _create_text_clip(
        self,
        text: str,
        font_size: int = 48,
        font: str = "Arial",
        color: tuple = (255, 255, 255),
        max_width: Optional[int] = None,
    ) -> TextClip:
        """Erstellt einen Text-Clip."""
        # Text umbrechen wenn nötig
        if max_width:
            text = self._wrap_text(text, font, font_size, max_width)

        return TextClip(
            text,
            fontsize=font_size,
            font=font,
            color=f"rgb{color}",
            method="caption" if "\n" in text else "label",
            size=(max_width, None) if max_width else None,
            align="center",
        )

    def _create_watermark(self) -> TextClip:
        """Erstellt das Branding-Watermark."""
        watermark = TextClip(
            self.config.watermark_text,
            fontsize=24,
            font=self.config.body_font,
            color=f"rgb{self.config.accent_color}",
        )
        watermark = watermark.set_position((20, self.config.height - 50))
        return watermark

    def _wrap_text(self, text: str, font: str, font_size: int, max_width: int) -> str:
        """Bricht Text um damit er in die maximale Breite passt."""
        words = text.split()
        lines = []
        current_line = []

        # Einfache Heuristik: ca. 10 Pixel pro Zeichen
        chars_per_line = max_width // (font_size // 2)

        for word in words:
            if len(" ".join(current_line + [word])) <= chars_per_line:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)

    def _safe_filename(self, name: str) -> str:
        """Erstellt einen sicheren Dateinamen."""
        return "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()

    def add_background_music(
        self,
        video_path: Path | str,
        music_path: Path | str,
        volume: float = 0.1,
        output_path: Optional[Path | str] = None,
    ) -> Path:
        """
        Fügt Hintergrundmusik zu einem Video hinzu.

        Args:
            video_path: Pfad zum Video
            music_path: Pfad zur Musikdatei
            volume: Lautstärke der Musik (0.0 - 1.0)
            output_path: Ausgabepfad

        Returns:
            Pfad zum Video mit Musik
        """
        from moviepy.editor import CompositeAudioClip

        video = VideoFileClip(str(video_path))
        music = AudioFileClip(str(music_path))

        # Musik auf Video-Länge anpassen
        if music.duration > video.duration:
            music = music.subclip(0, video.duration)
        else:
            # Musik loopen
            loops_needed = int(video.duration / music.duration) + 1
            music = concatenate_audioclips([music] * loops_needed).subclip(0, video.duration)

        # Lautstärke anpassen
        music = music.volumex(volume)

        # Audio kombinieren
        if video.audio:
            final_audio = CompositeAudioClip([video.audio, music])
        else:
            final_audio = music

        video = video.set_audio(final_audio)

        if not output_path:
            output_path = video_path.parent / f"{video_path.stem}_with_music{video_path.suffix}"

        video.write_videofile(
            str(output_path),
            fps=self.config.fps,
            codec=self.config.video_codec,
            audio_codec=self.config.audio_codec,
        )

        video.close()
        music.close()

        return Path(output_path)


def concatenate_audioclips(clips):
    """Hilfsfunktion zum Verbinden von Audio-Clips."""
    from moviepy.editor import concatenate_audioclips as concat

    return concat(clips)
