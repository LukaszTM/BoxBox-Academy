"""Opis gry dla reszty programu (patrz boxbox/games/__init__.py)."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GameAdapter:
    id: str  # krótki identyfikator w bazie i plikach, np. "f1_25"
    name: str  # nazwa dla człowieka
    source: str  # "udp" | "shared_memory" | "file"
    default_port: int | None
    tc_levels: dict[int, str]  # poziom z telemetrii -> nazwa dla gracza
    has_abs: bool
    has_ers: bool
    has_drs: bool
    assist_steps: tuple[str, ...]  # kroki zdejmowania asyst w kolejności
    formats: tuple[int, ...] = field(default_factory=tuple)  # obsługiwane formaty pakietów (dla UDP)
    hidden: bool = False  # nie pokazuj w oknie (np. w przygotowaniu)
