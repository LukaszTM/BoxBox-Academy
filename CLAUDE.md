# BoxBox Academy

Aplikacja PC w Pythonie: odbiera telemetrię UDP z F1 25 i mówi do gracza
głosem mechanika-instruktora. Tryb nauki (jazda bez asyst dla początkujących)
+ tryb wyścigowy (inżynier na radiu). Pełny plan: PLAN.md.

## Zasady
- Python 3.12, pytest, typowanie w całym kodzie.
- Silnik (coach/, engineer/) nigdy nie dotyka UI ani dźwięku - zwraca listę komunikatów.
- Każda nowa reguła trenera ma test na nagranym pakiecie UDP z recordings/.
- Nie dodawaj zależności bez pytania.
- Komentarze i komunikaty dla gracza po polsku, nazwy w kodzie po angielsku.
- Ton komunikatów: spokojny instruktor, konkretnie, bez krzyku.
- Przed zmianą sprawdź, czy etap z PLAN.md jest zakończony (kryterium ukończenia).

## Komendy
- Testy: `pytest`
- Uruchomienie: `python -m boxbox.app --mode coach`
- Odtworzenie nagrania zamiast gry: `python -m boxbox.app --replay recordings/<plik>`
