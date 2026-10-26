"""Katalog fraz głosowych: id klipu -> tekst do wygenerowania (raz, przez TTS) i składanie komunikatów.

Zasada składania: zakręt jako osobna fraza w mianowniku ("Zakręt czwarty."), potem
stały początek komunikatu, opcjonalnie liczba kończąca zdanie ("o jakieś
pięćdziesiąt metrów."), na końcu wskazówka jako całe zdanie. Jedno sklejenie
w zdaniu zamiast trzech, bez odmiany nazwy zakrętu przez przypadki.

Eksport listy do CSV dla skryptu TTS: python -m boxbox.voice.phrases --csv assets/voice/phrases.csv
"""
import argparse
import csv
import re
from collections.abc import Sequence
from pathlib import Path

from boxbox.coach.rules import Message

ORDINAL = [
    "", "pierwszy", "drugi", "trzeci", "czwarty", "piąty", "szósty", "siódmy", "ósmy", "dziewiąty",
    "dziesiąty", "jedenasty", "dwunasty", "trzynasty", "czternasty", "piętnasty", "szesnasty",
    "siedemnasty", "osiemnasty", "dziewiętnasty", "dwudziesty",
]
ORDINAL_GEN = [
    "", "pierwszego", "drugiego", "trzeciego", "czwartego", "piątego", "szóstego", "siódmego", "ósmego",
    "dziewiątego", "dziesiątego", "jedenastego", "dwunastego", "trzynastego", "czternastego",
    "piętnastego", "szesnastego", "siedemnastego", "osiemnastego", "dziewiętnastego", "dwudziestego",
]
TENS = ["", "dziesięć", "dwadzieścia", "trzydzieści", "czterdzieści", "pięćdziesiąt", "sześćdziesiąt",
        "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt"]
HUNDREDS = ["", "sto", "dwieście", "trzysta"]
MAX_CORNER = 20
METERS = tuple(range(10, 301, 10))

# Komunikaty: początek (może kończyć się "o jakieś", wtedy następuje liczba) i wskazówka.
RULE_TEXTS: dict[str, tuple[str, str]] = {
    "brake_late": ("Hamowanie za późno, o jakieś", "Zacznij hamować wcześniej i puszczaj pedał stopniowo."),
    "brake_late_big": ("Hamowanie dużo za późno, musiałeś mocno zwolnić, o jakieś",
                       "Następnym razem zacznij hamować dużo wcześniej."),
    "brake_early": ("Hamowanie za wcześnie, o jakieś", "Do apeksu dojeżdżasz z zapasem, możesz hamować później."),
    "brake_release": ("Hamulec puszczony naraz.", "Zwalniaj go stopniowo, aż do apeksu."),
    "trail_missing": ("Hamowanie kończy się za wcześnie.", "Trzymaj lekki hamulec do apeksu, auto lepiej skręci."),
    "throttle_late": ("Pełny gaz za późno na wyjściu, o jakieś", "Gdy kierownica się prostuje, dodawaj gaz pewniej."),
    "throttle_early": ("Gaz za wcześnie na wyjściu, koła ślizgają się zamiast przyspieszać.",
                       "Poczekaj z pełnym gazem, aż auto się wyprostuje."),
    "grip_lost_throttle": ("Utrata przyczepności.", "Łagodniej z gazem na wyjściu, zwłaszcza bez kontroli trakcji."),
    "grip_lost_entry": ("Utrata przyczepności.", "Wolniej na wejściu i mniej kierownicy, zanim dodasz gaz."),
    "gear_low": ("Za niski bieg.", ""),  # wskazówką jest klip biegu
    "gear_high": ("Za wysoki bieg, silnik nie ma siły.", ""),
}

MISC_TEXTS: dict[str, str] = {
    "hello": "Mechanik na radiu, słyszę cię. Jedź spokojnie, najpierw czyste okrążenie.",
    "lap_summary": "Podsumowanie okrążenia.",
    "lap_clean": "Czyste okrążenie, nic do poprawy. Tak trzymaj.",
    "lap_best": "Nowe najlepsze okrążenie.",
    "lap_invalid": "Okrążenie nieważne, wyjazd poza tor.",
    "no_reference": "Pierwsze okrążenie zapisane jako odniesienie. Teraz spróbuj je poprawić.",
    "reference_loaded": "Mam twoje najlepsze okrążenie z poprzednich sesji. Porównuję do niego.",
    "out_lap": "Okrążenie wyjazdowe. Rozgrzej opony, ocena od następnego.",
    "biggest_loss": "Czyste okrążenie. Najwięcej do zyskania:",
    "session_end": "Koniec sesji. Dobra robota.",
}


def corner_key(name: str) -> str:
    """'T9-T10' -> 't9_10', 'T4' -> 't4'; nazwy spoza wzorca T<n> dostają klucz 'zone'."""
    nums = re.findall(r"\d+", name)
    if name.upper().startswith("T") and nums:
        return "t" + "_".join(nums)
    return "zone"


def corner_text(name: str) -> str:
    nums = [int(n) for n in re.findall(r"\d+", name)]
    if not nums or not name.upper().startswith("T") or max(nums) > MAX_CORNER:
        return "Ten zakręt."
    if len(nums) == 1:
        return f"Zakręt {ORDINAL[nums[0]]}."
    a, b = nums[0], nums[-1]
    if b - a == 1:
        return f"Zakręty {ORDINAL[a]} i {ORDINAL[b]}."
    return f"Zakręty od {ORDINAL_GEN[a]} do {ORDINAL_GEN[b]}."


def meters_text(value: int) -> str:
    h, rest = divmod(value, 100)
    words = [w for w in (HUNDREDS[h], TENS[rest // 10]) if w]
    return " ".join(words) + " metrów."


def gear_text(gear: int) -> str:
    return f"W apeksie {ORDINAL[gear]} bieg."


def catalog(corner_names: Sequence[str] = ()) -> dict[str, str]:
    """Pełny słownik id -> tekst. Zakręty: wszystkie T1..T20 plus kombinacje z plików torów."""
    out: dict[str, str] = {}
    for n in range(1, MAX_CORNER + 1):
        out[f"corner_t{n}"] = corner_text(f"T{n}")
    for name in corner_names:
        out[f"corner_{corner_key(name)}"] = corner_text(name)
    for rule, (head, hint) in RULE_TEXTS.items():
        out[f"rule_{rule}_a"] = head
        if hint:
            out[f"rule_{rule}_b"] = hint
    for v in METERS:
        out[f"num_{v}"] = meters_text(v)
    for g in range(1, 9):
        out[f"gear_{g}"] = gear_text(g)
    for key, text in MISC_TEXTS.items():
        out[f"misc_{key}"] = text
    return out


def rule_variant(message: Message) -> str:
    if message.rule == "brake_late" and message.variant == "big":
        return "brake_late_big"
    if message.rule == "grip_lost":
        return "grip_lost_throttle" if message.variant == "throttle" else "grip_lost_entry"
    return message.rule


def compose(message: Message) -> list[str]:
    """Kolejność klipów dla komunikatu trenera."""
    rule = rule_variant(message)
    head, hint = RULE_TEXTS[rule]
    clips = [f"corner_{corner_key(message.corner_name)}", f"rule_{rule}_a"]
    if head.endswith("o jakieś"):
        clips.append(f"num_{message.value_m if message.value_m is not None else 10}")
    if hint:
        clips.append(f"rule_{rule}_b")
    if message.gear is not None and rule.startswith("gear"):
        clips.append(f"gear_{min(8, max(1, message.gear))}")
    return clips


def compose_short(message: Message) -> list[str]:
    """Jedno krótkie zdanie tuż po zakręcie: zakręt + problem (+ liczba), bez wskazówki."""
    rule = rule_variant(message)
    head, _ = RULE_TEXTS[rule]
    clips = [f"corner_{corner_key(message.corner_name)}", f"rule_{rule}_a"]
    if head.endswith("o jakieś"):
        clips.append(f"num_{message.value_m if message.value_m is not None else 10}")
    if message.gear is not None and rule.startswith("gear"):
        clips.append(f"gear_{min(8, max(1, message.gear))}")
    return clips


def spoken_text(message: Message, short: bool = False) -> str:
    """Dokładnie to, co mówi głos (te same frazy i zaokrąglone liczby), do konsoli i logu."""
    rule = rule_variant(message)
    head, hint = RULE_TEXTS[rule]
    parts = [corner_text(message.corner_name), head]
    if head.endswith("o jakieś"):
        value = message.value_m if message.value_m is not None else 10
        parts[-1] = head + " " + meters_text(value)
    if message.gear is not None and rule.startswith("gear"):
        parts.append(gear_text(min(8, max(1, message.gear))))
    elif hint and not short:
        parts.append(hint)
    return " ".join(parts)


def track_corner_names() -> list[str]:
    """Nazwy zakrętów ze wszystkich plików torów w boxbox/tracks/data."""
    import json
    names: list[str] = []
    for path in sorted((Path(__file__).parent.parent / "tracks" / "data").glob("*.json")):
        for c in json.loads(path.read_text(encoding="utf-8"))["corners"]:
            if c.get("name") and c["name"] not in names:
                names.append(c["name"])
    return names


def write_csv(path: Path, entries: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "text"])
        for key, text in entries.items():
            w.writerow([key, text])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Katalog fraz głosowych")
    parser.add_argument("--csv", type=Path, help="zapisz listę do CSV (id,text)")
    args = parser.parse_args(argv)
    entries = catalog(track_corner_names())
    chars = sum(len(t) for t in entries.values())
    print(f"{len(entries)} fraz, {chars} znaków")
    if args.csv:
        write_csv(args.csv, entries)
        print(f"zapisano {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
