"""Ustawienia i profil gracza w data/settings.json (lokalnie, bez chmury)."""
import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from boxbox.telemetry.udp import DEFAULT_PORT

DEFAULT_PATH = Path("data") / "settings.json"


@dataclass
class Settings:
    player_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    nick: str = ""
    photo: str = ""  # ścieżka do skopiowanego zdjęcia w data/
    photo_fit: dict = field(default_factory=dict)  # ręczne dopasowanie zdjęcia: x, y (0–100 %), zoom (100–300 %)
    volume: float = 1.5
    overlay: bool = True
    overlay_scale: float = 1.0
    port: int = DEFAULT_PORT
    game: str = "f1_25"  # adapter gry (boxbox/games); wybór w oknie ukryty, dopóki jest jedna gra
    voice_dir: str = "assets/voice"
    record: bool = True
    auto_start: bool = True  # trener startuje sam, gdy gra zacznie wysyłać telemetrię
    auto_stop_s: int = 20  # sesja kończy się sama po tylu sekundach bez pakietów (menu, wyjście z gry)
    wizard_done: bool = False
    tutorial_done: bool = False
    quiet: bool = False  # tryb cicho domyślnie (uwagi tylko po okrążeniu)
    explain: bool = False  # tryb „wytłumacz mi”
    consent: bool = False  # anonimowe statystyki do przyszłego rankingu (nic nie jest wysyłane w becie)
    overlay_opacity: int = 86  # krycie nakładki w %
    since: str = field(default_factory=lambda: __import__("datetime").date.today().strftime("%m.%Y"))
    last_session: dict = field(default_factory=dict)  # podsumowanie ostatniej sesji do ekranu Start
    lesson_state: dict = field(default_factory=dict)  # id lekcji -> {"best": n, "passed": bool}
    hud_layout: dict = field(default_factory=dict)  # układ nakładki HUD: positions, visible, opacity, scale (edytor w zakładce HUD F1)

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "Settings":
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {k: v for k, v in doc.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def save(self, path: Path = DEFAULT_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1), encoding="utf-8")
