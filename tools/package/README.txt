BoxBox Academy - trener jazdy do F1 25 (partia testowa 1)

Pelna instrukcja nagran: BoxBox_Academy_instrukcja_nagran.pdf. Protokol testu tej partii: TEST_PARTIA_1.txt.
Wymagania: Python 3.12+ (py -3 --version), z tkinter (domyslnie w instalatorze z python.org).

KROK 0 - GLOS (raz, ElevenLabs Creator):
  wygeneruj_glos.bat   -> pyta o klucz API i ID glosu, pokazuje liczbe znakow (ok. 40 tys.),
                          generuje tylko brakujace klipy, potem sam naklada efekt radia.
  Klucza API nie wpisuj do zadnego pliku i nie wklejaj na czacie.
  Potem spakuj assets\voice\raw do ZIP i przeslij (klipy trafia do repozytorium).

TEST GLOSNIKOW: glos-test.bat (powitanie + przykladowy komunikat; bez gry)

TRENER NA ZYWO Z GLOSEM I NAKLADKA:
  trener.bat <nazwa sesji>         np. trener.bat monza partia1
  Mowi po zakrecie i po okrazeniu, nakladka pokazuje okrazenie, najblizszy zakret i ostatnie
  3 komunikaty mechanika oraz krok asyst. Esc na nakladce albo Ctrl+C w terminalu konczy sesje:
  tabela zakretow, postep i obciazenie CPU. Nagranie trafia do recordings\.
  Gra w trybie okna bez ramki (nie pelny ekran). Potrzebny plik toru: Bahrajn, Monza, Suzuka.
  Nie laczyc z nakladka.bat ani nagraj.bat (jeden program na port UDP).

POSTEP: postep.bat  -> krok asyst, czyste okrazenia z rzedu, najlepsze czasy per krok, zakrety opanowane.

NAKLADKA DO NAGRAN (plan sesji, bez trenera):
  nakladka.bat <nazwa>             np. nakladka.bat monza trening z AI
  Plan dobiera sie po pierwszym slowie: bahrajn / monza / suzuka / pakiet2026.

SAMO NAGRYWANIE: nagraj.bat <nazwa>   (Ctrl+C konczy)
Sprawdzenie:  sprawdz.bat recordings\<plik>.bin
Po sesji: spakuj.bat recordings\<plik>.bin -> .bin.xz (lub czesci .part001... gdy > 24 MB).
Wyslij .bin.xz (albo wszystkie czesci) razem z .txt: GitHub, galaz claude/new-session-t6gmj8,
folder recordings, Add file -> Upload files. Dolacz tez data\boxbox.sqlite (baza okrazen i postepu).

Linux/macOS: python3 -m boxbox.app --mode coach --overlay --record <nazwa>
