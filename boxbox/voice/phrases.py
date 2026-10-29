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
from collections.abc import Callable, Sequence
from pathlib import Path

from boxbox.coach.rules import Message
from boxbox.coach.sectors import LOSS_TEXTS, NEXT_TEXTS, SECTOR_TEXTS
from boxbox.engineer.phrases import engineer_catalog

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
ORDINAL_LOC = [  # miejscownik/narzędnik: "w zakręcie czwartym", "przed zakrętem czwartym"
    "", "pierwszym", "drugim", "trzecim", "czwartym", "piątym", "szóstym", "siódmym", "ósmym", "dziewiątym",
    "dziesiątym", "jedenastym", "dwunastym", "trzynastym", "czternastym", "piętnastym", "szesnastym",
    "siedemnastym", "osiemnastym", "dziewiętnastym", "dwudziestym",
]
TENS = ["", "dziesięć", "dwadzieścia", "trzydzieści", "czterdzieści", "pięćdziesiąt", "sześćdziesiąt",
        "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt"]
V2_BUCKETS = (20, 50, 100, 150, 200, 300)  # liczby w pełnych zdaniach v2 (mniej klipów)
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

# Katalog v2: pełne zdanie z nazwą zakrętu w poprawnym przypadku (bez sklejania w środku zdania).
# {loc} = "zakręcie czwartym", {instr} = "zakrętem czwartym", {gen} = "zakrętu czwartego", {num} = liczba.
V2_TEXTS: dict[str, str] = {
    "brake_late": "Hamowanie za późno w {loc}, o jakieś {num}",
    "brake_late_big": "Hamowanie dużo za późno w {loc}, o jakieś {num} Musiałeś mocno zwolnić.",
    "brake_early": "Hamowanie za wcześnie w {loc}, o jakieś {num}",
    "throttle_late": "Pełny gaz za późno na wyjściu z {gen}, o jakieś {num}",
    "brake_release": "Hamulec puszczony naraz przed {instr}.",
    "trail_missing": "Hamowanie kończy się za wcześnie przed {instr}.",
    "throttle_early": "Gaz za wcześnie na wyjściu z {gen}, koła ślizgają się zamiast przyspieszać.",
    "grip_lost": "Utrata przyczepności w {loc}.",  # wspólne dla obu wariantów; różni się tylko wskazówka
    "gear_low": "Za niski bieg w {loc}.",
    "gear_high": "Za wysoki bieg w {loc}, silnik nie ma siły.",
}

MISC_TEXTS: dict[str, str] = {
    "hello": "Mechanik na radiu, słyszę cię. Jedź spokojnie, najpierw czyste okrążenie.",
    "lap_summary": "Podsumowanie okrążenia.",
    "lap_clean": "Czyste okrążenie, nic do poprawy. Tak trzymaj.",
    "lap_best": "Nowe najlepsze okrążenie.",
    "lap_invalid": "Okrążenie nieważne, wyjazd poza tor.",
    "no_reference": "Pierwsze okrążenie zapisane jako odniesienie. Teraz postaraj się je poprawić.",
    "reference_loaded": "Mam twoje najlepsze okrążenie z poprzednich sesji. Porównuję do niego.",
    "out_lap": "Okrążenie wyjazdowe. Rozgrzej opony, ocena od następnego.",
    "biggest_loss": "Czyste okrążenie. Najwięcej do zyskania:",
    "session_end": "Koniec sesji. Dobra robota.",
    "streak_1": "Czyste okrążenie, pierwsze z trzech.",
    "streak_2": "Czyste okrążenie, drugie z trzech.",
    "step_tc_medium": "Trzy czyste okrążenia z rzędu. Jesteś gotowy na kolejny krok: kontrola trakcji na średnią.",
    "step_tc_off": "Trzy czyste okrążenia z rzędu. Kolejny krok: kontrola trakcji wyłączona. Gaz dodawaj łagodniej na wyjściach.",
    "step_abs_off": "Trzy czyste okrążenia z rzędu. Kolejny krok: ABS wyłączony. Naciskaj hamulec mocno, ale nie do zablokowania kół.",
    "step_done": "Jedziesz bez asyst i masz trzy czyste okrążenia. Od teraz pracujemy nad czasem.",
    "ers_wasted": "Za dużo baterii idzie w zakrętach. Używaj jej na prostych, zaraz po wyjściu.",
    "ers_unused": "Bateria na mecie prawie pełna. Masz zapas na wyjściach z wolnych zakrętów.",
    "ers_last_lap": "Ostatnie okrążenie. Wciśnij całą baterię, co zostało.",
    "ers_empty_straight": "Bateria prawie pusta, a zaraz najdłuższa prosta. Oszczędzaj ją w zakrętach, wydawaj na prostych.",
    "ers_off_plan": "Bateria idzie w złych miejscach. Wydawaj ją na najdłuższych prostych, zaraz po wyjściu z zakrętu.",
    "drs_missed": "Nie włączyłeś DRS na prostej. Szukaj zielonej lampki zaraz po wyjściu z zakrętu.",
    "drs_late": "DRS włączony za późno. Naciskaj od razu, gdy zaświeci się zielona lampka.",
    "tyres_rear_hot": "Tył grzeje się bardziej niż przód. Łagodniej z gazem na wyjściach, opony podziękują.",
    "tyres_front_hot": "Przód grzeje się bardziej niż tył. Mniej kierownicy w zakręcie i wolniej na wejściu.",
    "tyres_side_hot": "Jedna strona opon dużo cieplejsza. Na tym torze to normalne, ale nie dociskaj w szybkich zakrętach.",
    "tyres_wear_fast": "Opony zużywają się szybko. Mniej ślizgania: płynniej gaz i mniej blokowania kół.",
    "tyres_wear_uneven": "Jedno koło zużyte dużo bardziej niż reszta. Zobacz w analizie, w których zakrętach ślizgasz.",
}


# Prowadzenie w zakręcie (boxbox/coach/guide_live.py): krótkie komendy przed punktem z okrążenia referencyjnego.
# "intro" idzie po klipie zakrętu: "Zakręt czwarty. Prowadzę." Reszta to pojedyncze słowa, bo liczy się czas.
# po okrążeniu: sektor z największą stratą (kubełek) i polecenie na następne okrążenie z liczbą metrów (klip num_)
MISC_TEXTS.update({f"sector_{n}": t for n, t in SECTOR_TEXTS.items()})
MISC_TEXTS.update({f"loss_{k}": t for k, t in LOSS_TEXTS.items()})
MISC_TEXTS.update({f"next_{k}": t for k, t in NEXT_TEXTS.items()})

TUTORIAL_TEXTS: dict[str, str] = {  # lektor samouczka w oknie: jeden klip na krok (kolejność jak TUTORIAL w app.js)
    "0": "Witaj w akademii. Tu zaczynasz każdy trening. Zostaw to okno otwarte i uruchom grę.",
    "1": "Zielona pastylka w rogu znaczy, że gra wysyła telemetrię. Szara: program czeka na grę.",
    "2": "Przycisk Jedź rozpoczyna sesję od razu. Przy starcie automatycznym ruszam sam, gdy przyjdzie telemetria.",
    "3": "W trakcie jazdy w tym panelu zobaczysz zbliżający się zakręt, bieżący cel i moje ostatnie komunikaty.",
    "4": "To twoja karta kierowcy: nick, identyfikator, poziom i statystyki. Plakietka na Starcie prowadzi tutaj.",
    "5": "Postęp: czyste okrążenia, trend czasów i krok asyst. Tu widzisz, co już opanowałeś i nad czym pracować.",
    "6": "Ustawienia: mój głos, nakładka HUD i zapis danych. Nakładka wymaga gry w oknie bez ramki. Do zobaczenia na torze.",
}

GUIDE_TEXTS: dict[str, str] = {
    "intro": "Prowadzę.",
    "lift": "Puść gaz.",
    "brake_hard": "Mocny hamulec.",  # bez „hamuj”: głos czyta „-uj” jako „-uć”
    "brake_medium": "Pół hamulca.",
    "brake_light": "Lekki hamulec.",
    "half": "Pół gazu.",
    "full": "Pełny gaz.",
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


def _corner_nums(name: str) -> list[int]:
    nums = [int(n) for n in re.findall(r"\d+", name)]
    if not nums or not name.upper().startswith("T") or max(nums) > MAX_CORNER:
        return []
    return nums


def corner_case(name: str, case: str) -> str:
    """Nazwa zakrętu w przypadku: 'loc' (w ...), 'instr' (przed ...), 'gen' (z ...)."""
    nums = _corner_nums(name)
    if not nums:
        return {"loc": "tym zakręcie", "instr": "tym zakrętem", "gen": "tego zakrętu"}[case]
    if len(nums) == 1:
        n = nums[0]
        return {"loc": f"zakręcie {ORDINAL_LOC[n]}", "instr": f"zakrętem {ORDINAL_LOC[n]}", "gen": f"zakrętu {ORDINAL_GEN[n]}"}[case]
    a, b = nums[0], nums[-1]
    plural = {"loc": "zakrętach", "instr": "zakrętami", "gen": "zakrętów"}[case]
    if b - a == 1:
        forms = ORDINAL_LOC if case in ("loc", "instr") else ORDINAL_GEN
        return f"{plural} {forms[a]} i {forms[b]}"
    return f"{plural} od {ORDINAL_GEN[a]} do {ORDINAL_GEN[b]}"


def bucket_m(value: int | None) -> int:
    v = value if value is not None else V2_BUCKETS[0]
    return min(V2_BUCKETS, key=lambda b: abs(b - v))


def _v2_rule(rule: str) -> str:
    return "grip_lost" if rule.startswith("grip_lost") else rule


def v2_text(rule: str, corner_name: str, value_m: int | None = None) -> str:
    template = V2_TEXTS[_v2_rule(rule)]
    text = template.format(
        loc=corner_case(corner_name, "loc"), instr=corner_case(corner_name, "instr"),
        gen=corner_case(corner_name, "gen"), num=meters_text(bucket_m(value_m)) if "{num}" in template else "",
    )
    return text.strip()


def v2_id(rule: str, corner_name: str, value_m: int | None = None) -> str:
    rule = _v2_rule(rule)
    base = f"v2_{rule}_{corner_key(corner_name)}"
    return f"{base}_{bucket_m(value_m)}" if "{num}" in V2_TEXTS[rule] else base


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
    for key, text in GUIDE_TEXTS.items():
        out[f"guide_{key}"] = text
    for key, text in TUTORIAL_TEXTS.items():
        out[f"tutorial_{key}"] = text
    out.update(engineer_catalog())  # inżynier (etap 6): generujemy razem, w jednym miesiącu planu
    from boxbox.coach.glossary import EXPLAIN  # tryb "wytłumacz mi": dłuższe wersje uwag (etap 8)

    for rule, text in EXPLAIN.items():
        out[f"explain_{rule}"] = text
    # v2: pełne zdania dla zakrętów z plików torów (+ ogólne "ten zakręt")
    names = list(corner_names) + ["zone"]
    for rule, template in V2_TEXTS.items():
        for name in names:
            if "{num}" in template:
                for b in V2_BUCKETS:
                    out[v2_id(rule, name, b)] = v2_text(rule, name, b)
            else:
                out[v2_id(rule, name)] = v2_text(rule, name)
    return out


def utterance(message: Message, available: "Callable[[str], bool] | None" = None, short: bool = False) -> tuple[list[str], str]:
    """(klipy, tekst) komunikatu: pełne zdanie v2, jeśli klip istnieje, inaczej składanie v1.

    `available` mówi, czy klip o danym id jest w bibliotece; bez niego zakładamy v1.
    """
    rule = rule_variant(message)
    head, hint = RULE_TEXTS[rule]
    v2 = v2_id(rule, message.corner_name, message.value_m)
    if available is not None and available(v2):
        ids = [v2]
        text = v2_text(rule, message.corner_name, message.value_m)
        if message.gear is not None and rule.startswith("gear"):
            g = min(8, max(1, message.gear))
            ids.append(f"gear_{g}")
            text += " " + gear_text(g)
        elif hint and not short:
            ids.append(f"rule_{rule}_b")
            text += " " + hint
        return ids, text
    ids = compose_short(message) if short else compose(message)
    return ids, spoken_text(message, short)


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
