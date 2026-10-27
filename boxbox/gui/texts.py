"""Wszystkie teksty okna w jednym miejscu: po polsku; w przyszłości angielski i lektor (samouczek)."""

APP_NAME = "BoxBox Academy"
VERSION = "0.6.0-beta"

NAV = {"home": "Start", "profile": "Karta kierowcy", "progress": "Postęp", "settings": "Ustawienia"}

HOME = {
    "title": "Trener na radiu",
    "subtitle": "Włącz w grze telemetrię UDP (port 20777), wyjedź na tor i naciśnij JEDŹ.",
    "go": "JEDŹ",
    "stop": "ZAKOŃCZ SESJĘ",
    "mode_coach": "Tryb nauki (trener)",
    "mode_race": "Tryb wyścigowy (inżynier, wkrótce)",
    "record": "Nagrywaj sesję (do analizy i zgłaszania błędów)",
    "overlay": "Nakładka na grę (okno zawsze na wierzchu)",
    "auto_start": "Start automatyczny: trener rusza sam, gdy gra zacznie wysyłać telemetrię (nie musisz wychodzić z gry)",
    "auto_started": "Gra wysyła telemetrię: trener wystartował sam.",
    "auto_stopped": "Brak sygnału z gry od {s} s: sesja zakończona automatycznie.",
    "name": "Nazwa sesji",
    "status_waiting": "Czekam na grę: brak pakietów na porcie {port}",
    "status_busy": "Port {port} zajęty: zamknij inny program z telemetrią",
    "status_ok": "Gra połączona: {track}, format {fmt}, {rate} pakietów/s",
    "live_lap": "OKRĄŻENIE {n}",
    "live_waiting": "czekam na telemetrię z gry...",
    "summary_title": "Podsumowanie sesji",
    "cpu": "Obciążenie: {cpu:.1f}% jednego rdzenia przez {wall:.0f} s",
    "messages": "Mechanik",
}

WIZARD = {
    "title": "Pierwsze uruchomienie",
    "steps": ["Telemetria", "Głośniki", "Asysty", "Kierowca"],
    "telemetry_intro": "W F1 25 wejdź w Ustawienia → Ustawienia telemetrii i ustaw jak w tabeli. Potem wróć tu i naciśnij Sprawdź.",
    "telemetry_rows": [
        ("Telemetria UDP", "Wł."), ("Tryb rozgłaszania UDP", "Wył."), ("Adres IP UDP", "127.0.0.1"),
        ("Port UDP", "20777"), ("Częstotliwość wysyłania", "60 Hz"), ("Format UDP", "2025 albo 2026"),
        ("Twoja telemetria", "Publiczna"),
    ],
    "check": "Sprawdź (nasłuch 5 s)",
    "checking": "Nasłuchuję...",
    "check_ok": "Jest telemetria: {track}, format {fmt}, {rate} pakietów/s. Możesz iść dalej.",
    "check_none": "Nic nie dotarło. Sprawdź, czy gra jest uruchomiona i jesteś w sesji (nie w menu), i czy port to 20777.",
    "check_busy": "Port zajęty przez inny program (trener w terminalu, nakładka, inna aplikacja telemetrii). Zamknij go i spróbuj ponownie.",
    "check_format": "Telemetria dociera, ale format {fmt} nie jest obsługiwany. Ustaw w grze Format UDP na 2025 lub 2026.",
    "speakers_intro": "Naciśnij Odtwórz. Powinieneś usłyszeć powitanie mechanika. Jeśli nie, sprawdź urządzenie wyjściowe dźwięku w Windows i głośność.",
    "play": "Odtwórz powitanie",
    "heard": "Słyszę",
    "not_heard": "Nie słyszę",
    "no_clips": "Brak klipów głosu w {path}. Wygeneruj je skryptem wygeneruj_glos.bat.",
    "assists_intro": "Zalecane ustawienia na start. Trener prowadzi przez kolejne kroki: po 3 czystych okrążeniach z rzędu powie, co zdjąć.",
    "assists_rows": [
        ("Skrzynia biegów", "automatyczna (krok 1)"), ("Kontrola trakcji", "pełna (krok 1)"), ("ABS", "włączony (krok 1)"),
        ("Linia jazdy", "pełna, zostaje"), ("Asysta ERS", "wyłączona, jeśli chcesz uwagi o baterii"), ("Flashback", "nie używaj podczas sesji"),
    ],
    "driver_intro": "Jak mam się do ciebie zwracać? Nick i zdjęcie są tylko na tym komputerze.",
    "nick": "Nick",
    "finish": "Zakończ i przejdź do startu",
    "next": "Dalej",
    "back": "Wstecz",
}

PROFILE = {
    "title": "Karta kierowcy",
    "nick": "Nick",
    "id": "ID kierowcy",
    "photo_hint": "Przeciągnij zdjęcie tutaj albo wybierz plik poniżej",
    "choose_photo": "Wybierz zdjęcie z dysku",
    "sessions": "Sesje",
    "laps": "Okrążenia",
    "tracks": "Tory",
    "best": "Najlepszy czas",
    "step": "Krok asyst",
    "save": "Zapisz",
    "saved": "Zapisano",
}

PROGRESS = {
    "title": "Postęp",
    "no_data": "Brak zapisanych okrążeń. Zrób pierwszą sesję z trenerem.",
    "laps_table": ["Data", "Okr.", "Czas", "Ważne", "TC", "ABS", "Skrzynia"],
    "mastered": "Zakręty opanowane",
    "todo": "Do pracy",
    "none_yet": "jeszcze żaden",
}

SETTINGS = {
    "title": "Ustawienia",
    "volume": "Głośność mechanika",
    "overlay_scale": "Wielkość napisów nakładki",
    "port": "Port UDP",
    "voice_dir": "Folder klipów głosu",
    "tutorial": "Pokaż samouczek jeszcze raz",
    "wizard": "Uruchom kreator pierwszego uruchomienia",
    "save": "Zapisz",
}

TUTORIAL = [
    ("home", "nav_home", "To jest ekran startu. Tu uruchamiasz trenera, gdy gra działa i telemetria jest włączona."),
    ("home", "status", "Pasek stanu mówi, czy gra jest połączona. Gdy widzisz nazwę toru i liczbę pakietów na sekundę, wszystko gra."),
    ("home", "go", "Nie musisz nic klikać: zostaw to okno, uruchom grę i wyjedź na tor. Trener wystartuje sam, gdy gra wyśle telemetrię. JEDŹ służy do ręcznego startu."),
    ("home", "live", "W trakcie sesji widzisz tu okrążenie, najbliższy zakręt, ostatnie słowa mechanika i cel na okrążenie. To samo pokazuje nakładka na grze."),
    ("profile", "nav_profile", "Karta kierowcy: twój nick, zdjęcie i liczby z wszystkich sesji."),
    ("progress", "nav_progress", "Postęp: krok asyst na każdym torze, seria czystych okrążeń, zakręty opanowane i tabela przejazdów."),
    ("settings", "nav_settings", "Ustawienia: głośność, nakładka, port. Stąd też uruchomisz ten samouczek ponownie."),
]

TUTORIAL_NEXT = "Dalej"
TUTORIAL_DONE = "Zamknij"
TUTORIAL_STEP = "Samouczek {i}/{n}"
