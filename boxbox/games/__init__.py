"""Adaptery gier: jedna warstwa między grą a resztą programu.

Reszta programu widzi tylko: okrążenie, zakręt, prędkość, gaz, hamulec, bieg, asysty, bateria, opony.
Adapter mówi, skąd telemetria, jak nazywają się asysty i jakie mają poziomy, jak nazwać tor.
W becie jest jedna gra (F1 25 z 2026 Season Pack); wybór gry w oknie jest ukryty do czasu drugiej.
Nowa gra = nowy plik w tym pakiecie + wpis w GAMES + parser telemetrii; okno i baza bez zmian.
"""
from boxbox.games.base import GameAdapter
from boxbox.games.f1_25 import F1_25

__all__ = ["GameAdapter", "GAMES", "DEFAULT_GAME", "adapter", "track_key", "split_track_key"]

GAMES: dict[str, GameAdapter] = {F1_25.id: F1_25}
DEFAULT_GAME = F1_25.id


def adapter(game_id: str | None = None) -> GameAdapter:
    return GAMES.get(game_id or DEFAULT_GAME, F1_25)


def track_key(track_id: int, game_id: str = DEFAULT_GAME) -> str:
    """Identyfikator toru niezależny od gry: Monza z F1 25 to 'f1_25:11', Monza z innej gry to inny klucz."""
    return f"{game_id}:{track_id}"


def split_track_key(key: str) -> tuple[str, int]:
    game_id, _, num = key.partition(":")
    return game_id, int(num)
