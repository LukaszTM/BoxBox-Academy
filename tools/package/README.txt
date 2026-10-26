BoxBox Academy - recorder telemetrii F1 25

Pelna instrukcja: BoxBox_Academy_instrukcja_nagran.pdf (w tym folderze).

Wymagania: Python 3.12+ (py -3 --version), z tkinter (domyslnie w instalatorze z python.org).

TRENER NA ZYWO Z GLOSEM (etap 4):
  trener.bat <nazwa sesji>        np. trener.bat bahrajn glos test
  Mowi po zakrecie i po okrazeniu (potrzebny plik toru: Bahrajn, Monza, Suzuka). Ctrl+C konczy.
  Nie laczyc z nakladka.bat (jeden program na port UDP).

NAKLADKA + NAGRYWANIE:
  nakladka.bat <nazwa>             np. nakladka.bat monza trening z AI
  Nazwa moze miec spacje (zamienia je na myslniki). Plan dobiera sie po pierwszym slowie:
  bahrajn / monza / suzuka / pakiet2026. Recznie: nakladka.bat --plan suzuka-tt-bez-tc <nazwa>
  Gra w trybie okna bez ramki (nie pelny ekran). Esc na nakladce konczy nagranie.

SAMO NAGRYWANIE (bez nakladki):
  nagraj.bat <nazwa>               np. nagraj.bat bahrajn-tt
  Zatrzymanie: Ctrl+C w terminalu

Sprawdzenie:  sprawdz.bat recordings\<plik>.bin
Notatki:      recordings\<plik>.txt (uzupelnij po kazdej sesji)
Po sesji: spakuj.bat recordings\<plik>.bin  -> plik .bin.xz (lub czesci .part001... gdy > 24 MB).
Wyslij .bin.xz (albo wszystkie czesci) razem z .txt i .guide.json: GitHub, galaz claude/new-session-t6gmj8,
folder recordings, Add file -> Upload files.

Linux/macOS: python3 -m boxbox.ui.overlay --name <nazwa> --plan plany/<plan>.json

GLOS MECHANIKA (jednorazowo, ElevenLabs):
  wygeneruj_glos.bat   -> pyta o klucz API i ID glosu, pokazuje liczbe znakow, generuje assets\voice\raw\*.wav
  Potem spakuj assets\voice\raw do ZIP i przeslij.
