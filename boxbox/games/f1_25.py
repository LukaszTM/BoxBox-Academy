"""F1 25 (EA/Codemasters) z 2026 Season Pack: telemetria UDP, formaty 2025 i 2026."""
from boxbox.games.base import GameAdapter
from boxbox.telemetry.header import SUPPORTED_FORMATS
from boxbox.telemetry.udp import DEFAULT_PORT

F1_25 = GameAdapter(
    id="f1_25",
    name="F1 25",
    source="udp",
    default_port=DEFAULT_PORT,
    tc_levels={0: "wyłączona", 1: "średnia", 2: "pełna"},
    has_abs=True,
    has_ers=True,
    has_drs=True,
    assist_steps=("automat, TC pełna, ABS", "TC średnia", "TC wyłączona", "ABS wyłączony"),
    formats=tuple(SUPPORTED_FORMATS),
)
