"""Trening względem najlepszych na świecie: okrążenie mistrza z ducha rankingu Time Trial.

Gra wysyła przez UDP telemetrię ducha wybranego z rankingu (np. nr 1 na świecie). Program zapamiętuje
jego najlepsze pełne okrążenie dla toru (bez nazwiska: w bazie zostaje tylko „duch z rankingu”),
a trener po każdym ważnym okrążeniu mówi, ile gracz traci do najlepszych i w którym zakręcie najwięcej,
z jedną wskazówką: najlepsi hamują później / dodają gaz wcześniej / są szybsi w apeksie. Cel na dziś
to połowa różnicy, nie cała: różnica do mistrza bywa kilkadziesiąt metrów i tego nie da się zrobić
w jednym okrążeniu.
"""
from dataclasses import dataclass

from boxbox.coach.compare import compare_to_reference
from boxbox.coach.corners import LapAnalysis
from boxbox.coach.sectors import LOSS_TEXTS, loss_bucket, next_lap_step_m

MIN_GAP_MS = 300  # poniżej tej różnicy do mistrza nie ma o czym mówić
BRAKE_LATER_MIN_M = 10.0
THROTTLE_EARLIER_MIN_M = 10.0
APEX_SLOWER_MIN_KMH = 8
MASTER_TEXTS: dict[str, str] = {
    "master_intro": "Mam okrążenie najlepszych na tym torze. Porównuję też do nich.",
    "master_gap": "Do najlepszych na świecie tracisz",
    "master_in": "Najwięcej w",
    "master_brake_later": "Najlepsi hamują tu później, o jakieś",
    "master_throttle_earlier": "Najlepsi dodają pełny gaz wcześniej, o jakieś",
    "master_apex": "Najlepsi są tu w apeksie wyraźnie szybsi: wchodzą z większą prędkością i trzymają ją.",
    "master_target_half": "Cel na dziś: połowa tej różnicy.",
}


@dataclass(frozen=True)
class MasterGap:
    total_ms: int  # strata całego okrążenia do mistrza
    corner: int  # zakręt z największą stratą czasu
    corner_loss_ms: int
    hint: str  # brake_later | throttle_earlier | apex | none
    hint_m: int  # metry do wypowiedzenia (0 dla apex/none), krok na dziś = połowa, 5-20 m


def master_gap(own: LapAnalysis, master: LapAnalysis) -> MasterGap | None:
    """Największa strata do mistrza: z czasu zakrętów; wskazówka z punktu hamowania, gazu albo apeksu."""
    if own.lap_time_ms is None or master.lap_time_ms is None:
        return None
    deltas = compare_to_reference(own, master)
    if not deltas:
        return None
    worst = max(deltas, key=lambda d: d.time_delta_ms)
    if worst.time_delta_ms < MIN_GAP_MS:
        return None
    hint, meters = "none", 0
    if worst.brake_point_delta_m is not None and -worst.brake_point_delta_m >= BRAKE_LATER_MIN_M:  # mistrz hamuje dalej = później
        hint, meters = "brake_later", int(round(-worst.brake_point_delta_m))
    elif worst.full_throttle_delta_m is not None and worst.full_throttle_delta_m >= THROTTLE_EARLIER_MIN_M:  # mistrz na gazie wcześniej
        hint, meters = "throttle_earlier", int(round(worst.full_throttle_delta_m))
    elif worst.min_speed_delta_kmh <= -APEX_SLOWER_MIN_KMH:
        hint = "apex"
    return MasterGap(max(0, own.lap_time_ms - master.lap_time_ms), worst.corner, worst.time_delta_ms, hint, meters)


def master_utterance(gap: MasterGap, corner_name: str) -> tuple[list[str], str]:
    """Klipy i tekst: strata, zakręt, wskazówka z krokiem na dziś (połowa różnicy, 5-20 m)."""
    from boxbox.voice.phrases import corner_key, corner_text, meters_text  # lokalnie: phrases importuje stąd teksty

    ids = ["misc_master_gap", f"misc_loss_{loss_bucket(gap.total_ms)}", "misc_master_in", f"corner_{corner_key(corner_name)}"]
    text = f"{MASTER_TEXTS['master_gap']} {LOSS_TEXTS[loss_bucket(gap.total_ms)]} {MASTER_TEXTS['master_in']} {corner_text(corner_name)}"
    if gap.hint in ("brake_later", "throttle_earlier"):
        num = max(10, min(300, round(gap.hint_m / 10) * 10))
        step = next_lap_step_m(gap.hint_m)
        ids += [f"misc_master_{gap.hint}", f"num_{num}", "misc_master_target_half"]
        text += f" {MASTER_TEXTS['master_' + gap.hint]} {meters_text(num)} {MASTER_TEXTS['master_target_half']}"
        text += f" ({step} m)"  # tylko do okna/dziennika: krok w metrach
    elif gap.hint == "apex":
        ids.append("misc_master_apex")
        text += f" {MASTER_TEXTS['master_apex']}"
    return ids, text


def format_gap(gap_ms: int | None) -> str:
    return "—" if gap_ms is None else f"−{gap_ms / 1000:.1f} s".replace(".", ",")
