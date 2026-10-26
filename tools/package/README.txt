BoxBox Academy - recorder telemetrii F1 25

Pelna instrukcja: BoxBox_Academy_instrukcja_nagran.pdf (w tym folderze).

Wymagania: Python 3.12+ (py -3 --version), z tkinter (domyslnie w instalatorze z python.org).

NAKLADKA + NAGRYWANIE (zalecane):
  nakladka.bat <nazwa>             np. nakladka.bat monza trening z AI
  Nazwa moze miec spacje (zamienia je na myslniki). Plan dobiera sie po pierwszym slowie:
  bahrajn / monza / suzuka / pakiet2026. Recznie: nakladka.bat --plan suzuka-tt-bez-tc <nazwa>
  Gra w trybie okna bez ramki (nie pelny ekran). Esc na nakladce konczy nagranie.

SAMO NAGRYWANIE (bez nakladki):
  nagraj.bat <nazwa>               np. nagraj.bat bahrajn-tt
  Zatrzymanie: Ctrl+C w terminalu

Sprawdzenie:  sprawdz.bat recordings\<plik>.bin
Notatki:      recordings\<plik>.txt (uzupelnij po kazdej sesji)
Po sesji spakuj .bin do ZIP/RAR (166 MB -> ok. 12 MB) i przeslij razem z .txt i .guide.json.

Linux/macOS: python3 -m boxbox.ui.overlay --name <nazwa> --plan plany/<plan>.json
