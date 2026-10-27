"""Katalog zdań inżyniera na radiu (tryb wyścigowy, etap 6).

Tylko teksty: reguły inżyniera powstaną w etapie 6, ale klipy generujemy razem
z resztą (jedno uruchomienie `wygeneruj_glos.bat`, jeden miesiąc planu ElevenLabs).
Identyfikatory klipów: `eng_<klucz>`; liczby okrążeń: `eng_laps_<n>`, sekundy: `eng_sec_<n>`.
"""

ENGINEER_TEXTS: dict[str, str] = {
    # start i ogólne
    "hello": "Inżynier na radiu. Pełny wyścig, spokojnie, trzymaj swoje tempo.",
    "formation_lap": "Okrążenie formacyjne. Grzej opony i hamulce, trzymaj pozycję.",
    "lights_out": "Start. Czysto przez pierwszy zakręt, pozycje odrobisz później.",
    "last_lap": "Ostatnie okrążenie. Nic już nie oszczędzaj.",
    "final_laps": "Zostały trzy okrążenia. Dowieź to do mety.",
    "race_end": "Meta. Dobra robota, wracaj do boksu.",
    "push_now": "Teraz możesz cisnąć, masz czysty tor przed sobą.",
    "manage_pace": "Zejdź z tempa o dwie dziesiąte, dowieziemy te opony.",
    # opony
    "tyres_cold": "Opony za zimne. Więcej pracy w zakrętach, ostrożnie na gazie.",
    "tyres_hot": "Opony przegrzane. Spokojniej na wyjściach, daj im odpocząć.",
    "tyres_window": "Opony w oknie. Tak trzymaj.",
    "tyres_front_wear": "Przednie opony się kończą. Nie wjeżdżaj za ostro, odpuść wejścia.",
    "tyres_rear_wear": "Tylne opony się kończą. Gaz łagodniej na wyjściach.",
    "tyres_critical": "Opony na granicy. Pit, jak tylko będzie okno.",
    "tyres_graining": "Zaczyna się ziarnienie, kilka okrążeń spokojniej i powinno zejść.",
    # pit-stop
    "pit_window_open": "Okno pit-stopu otwarte. Box na tym okrążeniu, potwierdź.",
    "pit_this_lap": "Box, box. Zjeżdżasz na tym okrążeniu.",
    "pit_next_lap": "Box na następnym okrążeniu. Bądź gotowy.",
    "pit_in": "Zjeżdżaj. Limiter przed linią, trafisz w boks.",
    "pit_out": "Wyjazd z boksu. Opony zimne, pierwsze okrążenie ostrożnie.",
    "pit_stay_out": "Zostań na torze, pit za chwilę.",
    "pit_undercut": "Rywal zjechał. Trzy mocne okrążenia i zjeżdżamy, bronimy pozycji.",
    "pit_to_wet": "Robi się mokro. Box na przejściówki.",
    "pit_to_dry": "Tor schnie. Box na slicki.",
    # flagi i safety car
    "flag_yellow": "Żółta flaga w sektorze. Zwolnij, bez wyprzedzania.",
    "flag_yellow_clear": "Tor czysty. Zielona, wracaj do tempa.",
    "flag_blue": "Niebieska flaga. Przepuść lidera, nie trać na tym tempa.",
    "flag_red": "Czerwona flaga. Wracaj spokojnie do boksu.",
    "safety_car": "Safety car. Trzymaj pozycję, grzej opony, nie wyprzedzaj.",
    "safety_car_in": "Safety car zjeżdża na tym okrążeniu. Bądź gotowy na restart.",
    "vsc": "Wirtualny safety car. Trzymaj deltę, zwolnij.",
    "vsc_end": "Koniec wirtualnego safety cara. Jedziemy.",
    "drs_enabled": "DRS dostępny. Używaj go na prostej.",
    "drs_disabled": "DRS wyłączony.",
    # odstępy
    "gap_ahead_close": "Masz auto przed sobą w zasięgu DRS. Do ataku.",
    "gap_ahead": "Do auta z przodu:",
    "gap_behind": "Auto z tyłu:",
    "gap_behind_close": "Rywal w zasięgu DRS. Broń się, ale tylko jedna zmiana toru.",
    "gap_safe": "Bezpieczna przewaga. Trzymaj tempo, bez ryzyka.",
    "position_gained": "Pozycja zyskana. Dobrze.",
    "position_lost": "Pozycja stracona. Spokojnie, odrobimy.",
    # uszkodzenia
    "damage_front_wing": "Uszkodzone przednie skrzydło. Auto będzie podsterowne.",
    "damage_front_wing_big": "Przednie skrzydło mocno uszkodzone. Box, wymieniamy.",
    "damage_floor": "Uszkodzona podłoga. Stracimy trochę przyczepności, jedź dalej.",
    "damage_rear_wing": "Uszkodzone tylne skrzydło. Ostrożnie w szybkich zakrętach.",
    "puncture": "Przebita opona. Box, box, natychmiast.",
    "engine_warn": "Silnik ma problemy. Oszczędzaj, dojedź do boksu.",
    # paliwo i ERS
    "fuel_ok": "Paliwo w porządku.",
    "fuel_save": "Oszczędzaj paliwo. Krótsze zmiany biegów, wcześniej odpuszczaj gaz.",
    "fuel_push": "Masz zapas paliwa. Możesz cisnąć.",
    "ers_deploy": "Baterię używaj na prostych, mamy dużo zapasu.",
    "ers_save": "Oszczędzaj baterię do ataku na następnym okrążeniu.",
    # pogoda
    "rain_coming": "Deszcz za kilka minut. Bądź gotowy na mokry tor.",
    "rain_now": "Pada. Zacznij hamować wcześniej, szukaj przyczepności poza linią.",
    "track_drying": "Tor schnie. Linia wyścigowa jest najsuchsza.",
    # kary
    "penalty_time": "Masz karę czasową. Odjedziesz ją na mecie.",
    "penalty_warning": "Ostrzeżenie za limity toru. Zostaw sobie margines.",
    "collision": "Kontakt. Sprawdź, czy auto jedzie prosto.",
    # odpowiedzi na pytania (komendy głosowe, etap 6)
    "answer_laps_left": "Do końca zostało:",
    "answer_position": "Twoja pozycja:",
    "answer_tyres": "Opony: zużycie w normie, temperatura w oknie.",
    "answer_weather": "Pogoda: bez zmian w najbliższych minutach.",
}

LAPS_TEXTS: dict[int, str] = {
    1: "jedno okrążenie",
    2: "dwa okrążenia",
    3: "trzy okrążenia",
    4: "cztery okrążenia",
    5: "pięć okrążeń",
    6: "sześć okrążeń",
    7: "siedem okrążeń",
    8: "osiem okrążeń",
    9: "dziewięć okrążeń",
    10: "dziesięć okrążeń",
    15: "piętnaście okrążeń",
    20: "dwadzieścia okrążeń",
}

SECONDS_TEXTS: dict[str, str] = {
    "half": "pół sekundy",
    "1": "sekunda",
    "2": "dwie sekundy",
    "3": "trzy sekundy",
    "4": "cztery sekundy",
    "5": "pięć sekund",
    "7": "siedem sekund",
    "10": "dziesięć sekund",
    "15": "piętnaście sekund",
    "20": "dwadzieścia sekund",
    "30": "ponad trzydzieści sekund",
}

POSITION_TEXTS: dict[int, str] = {
    1: "pierwsza", 2: "druga", 3: "trzecia", 4: "czwarta", 5: "piąta", 6: "szósta", 7: "siódma",
    8: "ósma", 9: "dziewiąta", 10: "dziesiąta", 11: "jedenasta", 12: "dwunasta", 13: "trzynasta",
    14: "czternasta", 15: "piętnasta", 16: "szesnasta", 17: "siedemnasta", 18: "osiemnasta",
    19: "dziewiętnasta", 20: "dwudziesta", 21: "dwudziesta pierwsza", 22: "dwudziesta druga",
    23: "dwudziesta trzecia", 24: "dwudziesta czwarta",
}


def engineer_catalog() -> dict[str, str]:
    """id klipu -> tekst, wszystkie klipy inżyniera (klipy liczbowe doklejane po zdaniach z dwukropkiem)."""
    out = {f"eng_{key}": text for key, text in ENGINEER_TEXTS.items()}
    out.update({f"eng_laps_{n}": text for n, text in LAPS_TEXTS.items()})
    out.update({f"eng_sec_{k}": text for k, text in SECONDS_TEXTS.items()})
    out.update({f"eng_pos_{n}": text for n, text in POSITION_TEXTS.items()})
    return out


def seconds_key(gap_s: float) -> str:
    """Najbliższy klip sekund dla odstępu (zaokrąglenie w dół do dostępnych wartości)."""
    if gap_s < 0.75:
        return "half"
    keys = [int(k) for k in SECONDS_TEXTS if k != "half"]
    best = max(k for k in keys if k <= max(1.0, gap_s)) if gap_s >= 1 else 1
    return str(best)
