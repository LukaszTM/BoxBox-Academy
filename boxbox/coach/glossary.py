"""Słownik pojęć i dłuższe wersje uwag do trybu „wytłumacz mi” (teksty, bez UI i bez głosu)."""

GLOSSARY: dict[str, tuple[str, str]] = {
    "apeks": ("Apeks", "Punkt zakrętu, w którym jedziesz najwolniej i jesteś najbliżej wewnętrznej krawędzi. Przed nim hamujesz, za nim dodajesz gazu."),
    "punkt_hamowania": ("Punkt hamowania", "Miejsce, gdzie zaczynasz hamować przed zakrętem. Trener porównuje je z twoim najlepszym okrążeniem i mówi, o ile metrów za wcześnie lub za późno."),
    "trail_braking": ("Trail-braking", "Stopniowe zwalnianie hamulca już po skręceniu, aż do apeksu. Dociąża przód i auto lepiej skręca."),
    "delta": ("Delta", "Różnica czasu między twoim przejazdem a referencją w danym miejscu toru. Rośnie tam, gdzie tracisz, maleje tam, gdzie zyskujesz."),
    "referencja": ("Okrążenie referencyjne", "Okrążenie, do którego trener porównuje twoją jazdę: twoje najlepsze z bazy, pierwsze pełne w sesji albo duch rywala z Time Trial."),
    "deploy": ("Deploy ERS", "Oddawanie energii z baterii do silnika. Najwięcej daje na prostych tuż po wyjściu z zakrętu; w zakrętach się marnuje."),
    "krok_asyst": ("Krok asyst", "Etap zdejmowania ułatwień: 1 automat i pełne asysty, 2 kontrola trakcji na średnią, 3 bez kontroli trakcji, 4 bez ABS. Trzy czyste okrążenia z rzędu otwierają kolejny krok."),
    "czyste_okrazenie": ("Czyste okrążenie", "Okrążenie ważne, bez pit lane i bez poważnego błędu (żadna uwaga trenera nie przekracza 1 s straty)."),
    "tc": ("Kontrola trakcji (TC)", "Asysta, która przycina gaz, gdy koła zaczynają się ślizgać. Bez niej gaz na wyjściu trzeba dawkować samemu."),
    "abs": ("ABS", "Asysta, która nie pozwala zablokować kół przy hamowaniu. Bez niej za mocne hamowanie blokuje koła i auto nie skręca."),
}

EXPLAIN: dict[str, str] = {
    "brake_late": "Hamujesz później niż na swoim najlepszym okrążeniu, więc dojeżdżasz do apeksu za szybko i musisz zwalniać w środku zakrętu. To kosztuje wyjście i całą prostą. Przesuń punkt hamowania wcześniej, ale puszczaj hamulec stopniowo.",
    "brake_early": "Hamujesz wcześniej niż na swoim najlepszym okrążeniu i do apeksu dojeżdżasz z zapasem prędkości. Możesz hamować później; zyskasz na wejściu bez ryzyka.",
    "brake_release": "Puściłeś hamulec naraz zamiast stopniowo. Auto nagle traci dociążenie przodu i gorzej skręca. Zwalniaj hamulec płynnie, aż do apeksu.",
    "trail_missing": "Hamowanie skończyło się za wcześnie przed apeksem. Lekki hamulec do apeksu dociąża przód i pozwala wejść w zakręt pewniej.",
    "throttle_late": "Pełny gaz przyszedł później niż na twoim najlepszym okrążeniu. Każdy metr bez gazu na wyjściu to strata na całej prostej. Dodawaj gaz, gdy kierownica się prostuje.",
    "throttle_early": "Gaz za wcześnie: koła ślizgają się zamiast przyspieszać, a bez kontroli trakcji auto może się obrócić. Poczekaj z pełnym gazem, aż auto się wyprostuje.",
    "grip_lost": "Prędkość w zakręcie spadła dużo bardziej niż zwykle: utrata przyczepności, obrót albo wyjazd. Następnym razem wolniej na wejściu i łagodniej z gazem.",
    "gear_low": "Za niski bieg w apeksie: silnik na obrotach, koła łatwo tracą przyczepność na gazie. Wrzuć o jeden wyżej przed apeksem.",
    "gear_high": "Za wysoki bieg w apeksie: silnik nie ma siły na wyjściu i tracisz na prostej. Zredukuj o jeden przed apeksem.",
}


def explain(rule: str) -> str:
    key = rule.replace("_big", "").replace("_throttle", "").replace("_entry", "")
    return EXPLAIN.get(key, "")
