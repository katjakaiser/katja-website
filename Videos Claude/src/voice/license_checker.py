"""
Lizenzprüfung für ElevenLabs.

Prüft vor jeder Video-Erstellung, ob ein aktives Abo mit Commercial License besteht.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionStatus:
    """Status des ElevenLabs-Abonnements."""

    is_active: bool
    tier: str  # free, starter, creator, pro
    has_commercial_license: bool
    character_count: int
    character_limit: int

    @property
    def characters_remaining(self) -> int:
        return max(0, self.character_limit - self.character_count)

    @property
    def can_use_commercially(self) -> bool:
        """Prüft ob kommerzielle Nutzung erlaubt ist."""
        return self.is_active and self.has_commercial_license


class LicenseChecker:
    """
    Prüft den ElevenLabs Lizenzstatus vor jeder Nutzung.

    WICHTIG: Voice Cloning darf nur mit aktivem, kostenpflichtigem
    Abo kommerziell genutzt werden!
    """

    # Tiers mit Commercial License
    COMMERCIAL_TIERS = ["starter", "creator", "pro", "enterprise"]

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            from elevenlabs import ElevenLabs
            self._client = ElevenLabs(api_key=self.api_key)
        return self._client

    def check_subscription(self) -> SubscriptionStatus:
        """
        Prüft den aktuellen Abo-Status bei ElevenLabs.

        Returns:
            SubscriptionStatus mit allen relevanten Informationen
        """
        client = self._get_client()

        try:
            # Subscription-Info abrufen
            user = client.user.get()
            subscription = user.subscription

            tier = subscription.tier.lower() if subscription.tier else "free"

            status = SubscriptionStatus(
                is_active=subscription.status == "active" if hasattr(subscription, 'status') else True,
                tier=tier,
                has_commercial_license=tier in self.COMMERCIAL_TIERS,
                character_count=subscription.character_count or 0,
                character_limit=subscription.character_limit or 0,
            )

            logger.info(f"ElevenLabs Abo: {status.tier}, Commercial: {status.has_commercial_license}")

            return status

        except Exception as e:
            logger.error(f"Fehler bei Abo-Prüfung: {e}")
            # Im Fehlerfall: Sicherheitshalber als nicht-kommerziell behandeln
            return SubscriptionStatus(
                is_active=False,
                tier="unknown",
                has_commercial_license=False,
                character_count=0,
                character_limit=0,
            )

    def verify_commercial_use(self) -> tuple[bool, str]:
        """
        Verifiziert ob kommerzielle Nutzung erlaubt ist.

        Returns:
            (erlaubt, nachricht)
        """
        status = self.check_subscription()

        if not status.is_active:
            return False, (
                "⚠️  WARNUNG: Dein ElevenLabs-Abo ist nicht aktiv!\n"
                "    Kommerzielle Nutzung der geklonten Stimme ist NICHT erlaubt.\n"
                "    Bitte aktiviere ein kostenpflichtiges Abo (mind. Starter)."
            )

        if not status.has_commercial_license:
            return False, (
                "⚠️  WARNUNG: Dein ElevenLabs-Plan hat KEINE Commercial License!\n"
                f"    Aktueller Plan: {status.tier}\n"
                "    Für kommerzielle YouTube-Videos brauchst du mind. den Starter-Plan ($5/Monat).\n"
                "    Die Nutzung der geklonten Stimme für dein Business ist rechtlich NICHT erlaubt."
            )

        if status.characters_remaining < 5000:
            return True, (
                f"⚠️  HINWEIS: Nur noch {status.characters_remaining} Zeichen übrig!\n"
                f"    Plan: {status.tier} ({status.character_count}/{status.character_limit} verbraucht)"
            )

        return True, (
            f"✓ Commercial License aktiv ({status.tier})\n"
            f"  Zeichen verfügbar: {status.characters_remaining:,}"
        )


# Warnung die bei jeder Nutzung angezeigt wird
COMMERCIAL_USE_WARNING = """
╔══════════════════════════════════════════════════════════════════╗
║                    WICHTIGER LIZENZHINWEIS                       ║
╠══════════════════════════════════════════════════════════════════╣
║  Die geklonte Stimme darf NUR mit aktivem ElevenLabs-Abo         ║
║  (mind. Starter-Plan) kommerziell genutzt werden.                ║
║                                                                  ║
║  Bei Kündigung des Abos:                                         ║
║  → Keine kommerzielle Nutzung mehr erlaubt                       ║
║  → Bereits veröffentlichte Videos müssen ggf. entfernt werden    ║
║                                                                  ║
║  Dieses Tool prüft automatisch deinen Abo-Status.                ║
╚══════════════════════════════════════════════════════════════════╝
"""
