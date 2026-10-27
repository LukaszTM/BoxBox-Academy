# BoxBox Academy – plan testów z przypadkami testowymi

Stan na 27.10.2026, gałąź `claude/new-session-t6gmj8`, po zakończeniu etapów 0–5 planu (PLAN.md).
Dokument zbiera testy już wykonane (automatyczne i na żywo z grą), ich wyniki oraz testy zaplanowane
na kolejne sesje. Formularz na jedną sesję jest na końcu.

## 1. Zakres i cele

Aplikacja odbiera telemetrię UDP z F1 25, dzieli okrążenie na zakręty, porównuje przejazd z okrążeniem
referencyjnym i mówi do gracza głosem mechanika. Testy mają potwierdzić, że:

- każdy pakiet z gry (format 2025 i 2026 Season Pack) jest poprawnie odczytany,
- zakręty i okrążenia są rozpoznawane na nagraniach z trzech torów (Bahrajn, Monza, Suzuka),
- reguły trenera wykrywają celowe błędy nagrane przez gracza i milczą na czystych okrążeniach,
- komunikat głosowy przychodzi na czas, jest zrozumiały i zgodny z tekstem w konsoli,
- ścieżka zdejmowania asyst, ekran postępu i baza działają po sesji,
- aplikacja nie obciąża komputera (cel: poniżej 10% jednego rdzenia).

Poza zakresem na dziś: tryb wyścigowy (inżynier), komendy głosowe, pakiet `.exe` (etap 6).

## 2. Środowisko testowe

| Element | Wartość |
| --- | --- |
| Gra | F1 25 (PC), telemetria UDP wł., port 20777, 60 Hz, format 2025 lub 2026 |
| Komputer gracza | Windows 11, Python 3.14, klon repozytorium w `D:\BOX BOX ACADEMY\repo` |
| Środowisko CI (chmura) | Linux, Python 3.13, `pytest`, bez tkinter i bez dźwięku |
| Głos | ElevenLabs, głos „Piotr – Neutral and Mature Bard”, 694 klipy z efektem radia |
| Nagrania wzorcowe | `recordings/`: bahrajn-tt, monza-trening, suzuka-tt-bez-tc, suzuka-bez-tc-pomiar, pakiet2026-monza, monza-partia1 |

## 3. Poziomy testów

1. **Testy automatyczne (`pytest`)**: 175 testów w 27 plikach, czas ok. 3 min. Uruchamiane po każdej zmianie, przed każdym commitem. Każda reguła trenera ma test na nagranym pakiecie UDP (zasada z CLAUDE.md).
2. **Odtworzenie nagrania (`--replay`)**: ten sam kod co na żywo, ale z pliku. Służy do odtwarzania błędów zgłoszonych z sesji bez ponownego jeżdżenia.
3. **Symulacja na żywo**: nagranie wysyłane przez UDP do działającej aplikacji z wątkiem nakładki i zapisem (narzędzie pomocnicze w chmurze). Sprawdza wątki, port, nagrywanie, bazę.
4. **Sesje z grą**: gracz jedzie według protokołu (`docs/TEST_PARTIA_1.md`), wypełnia formularz i przesyła nagranie, bazę i dziennik `data/boxbox.log`.

## 4. Przypadki testowe automatyczne (wykonane, wynik: zaliczone)

| ID | Obszar | Co sprawdza | Plik testu |
| --- | --- | --- | --- |
| A-01 | Nagłówek pakietu | Rozpoznanie formatu 2025/2026, id pakietu, odrzucenie zbyt krótkich i obcych pakietów | test_header.py |
| A-02 | Parsery pakietów | Car Telemetry, Lap Data, Session, Car Status, Car Damage, Event, Participants, Car Telemetry 2 (2026): rozmiary struktur zgodne ze specyfikacją EA, pola gracza i rywala | test_packets.py, test_session_status.py, test_event_damage.py |
| A-03 | Nagrania rzeczywiste | 5 nagrań z gry, oba formaty: 0 błędów parsera, liczby pakietów, tor i długość toru z pakietu Session | test_recordings.py |
| A-04 | Nagrywanie i odtwarzanie | Format pliku BBXREC01, kompresja xz, filtr zbędnych pakietów, odtwarzanie z czasem i bez czekania | test_record.py, test_replay.py |
| A-05 | Stan telemetrii | Łączenie pakietów w jeden stan gracza, liczniki formatów, pakiet MOTION (id 0) liczony poprawnie | test_console.py, test_packets.py |
| A-06 | Model toru | Zapis/odczyt JSON, zakręt dla dystansu, walidacja kolejności, wykrywanie zakrętów z minimów prędkości i pedałów, łączenie i przycinanie stref, zakręty bez hamowania | test_tracks.py, test_detect.py |
| A-07 | Okrążenia | Podział pakietów na okrążenia, odrzucenie pustych okrążeń z garażu, pit lane, nieważne, długość toru, głosowanie asyst per okrążenie | test_laps.py |
| A-08 | Metryki zakrętów | v_min, apeks jako środek plateau, bieg, punkt hamowania, koniec hamowania, czas puszczenia hamulca, pełny gaz | test_laps.py, test_rules.py |
| A-09 | Duch Time Trial | Prędkość ducha liczona z dystansu i czasu (pole prędkości z gry jest śmieciowe), okrążenie rywala jako referencja | test_ghost.py |
| A-10 | Reguły trenera | 9 reguł na nagranych celowych błędach: hamowanie za późno (zwykłe i „dużo”), za wcześnie, hamulec puszczony naraz, brak trail-brakingu, gaz za późno/za wcześnie, utrata przyczepności, bieg za niski/za wysoki; progi 0,3 s i 0,15 s; wybór 3 najważniejszych; nacisk bez TC/ABS | test_rules.py |
| A-11 | Trener na żywo | Powitanie, okrążenie wyjazdowe, referencja z bazy lub pierwsze okrążenie, komunikat po zakręcie 25–150 m za wyjściem, podsumowanie po okrążeniu, nowe najlepsze, koniec sesji | test_live.py |
| A-12 | ERS | Deploy per strefa, marnowanie w zakrętach, niewykorzystana bateria, brak rady przy asyście ERS | test_ers.py |
| A-13 | Postęp | Kroki asyst 1–4, seria 3 czystych okrążeń, reset po dużym błędzie, zmiana asyst, zapis w bazie, ekran `--progress` na nagraniu z Monzy | test_progress.py |
| A-14 | Baza SQLite | Sesje, okrążenia, metryki, próbki, komunikaty, postęp, migracja kolumn, najlepsze okrążenie, session_uid jako tekst | test_storage.py |
| A-15 | Katalog fraz | Pełny katalog 694 fraz, odmiana numerów zakrętów, pełne zdania v2 z koszykami metrów, składanie v1, zgodność tekstu konsoli z mową, limit znaków planu ElevenLabs | test_phrases.py |
| A-16 | Dźwięk | Efekt radia (pasmo 300–3400 Hz, ogranicznik, szum, klik), biblioteka klipów, kolejka odtwarzacza, głośność | test_voice.py |
| A-17 | Nakładka | Przewodniki torów i plany sesji, następny zakręt z zawijaniem na mecie, kalibracja z pierwszego okrążenia, lista zadań, widok trenera (okrążenie, zakręt, 3 ostatnie komunikaty) | test_overlay.py |
| A-18 | Aplikacja | Uruchomienie bez danych, replay z bazą, `--overlay` z telemetrią w wątku, dziennik `boxbox.log`, linie „Cel” i „popraw” | test_app.py |
| A-19 | Pakowanie | xz + podział na części 20 MB, sklejanie, pakowanie folderu do tar.xz | test_pack.py |
| A-20 | Pliki torów w repozytorium | Regresja: `data/` w `.gitignore` ukrył pliki torów przed klonem | test_tracks.py |

## 5. Sesje z grą (wykonane)

| ID | Data | Sesja | Wynik | Co znaleziono i naprawiono |
| --- | --- | --- | --- | --- |
| S-01 | 26.10 | Bahrajn TT, 6 okr., nagranie wzorcowe | OK | Pakiet MOTION liczony jako nieznany; session_uid nie mieścił się w SQLite; puste okrążenie z garażu |
| S-02 | 26.10 | Monza trening z AI, nagranie z nakładką | OK | Nazwy sesji ze spacjami w .bat; napisy nakładki słabo widoczne; przewodnik Monzy T1 źle podpisany; kalibracja z 1. okrążenia |
| S-03 | 26.10 | Suzuka TT bez TC + okrążenia pomiarowe | OK | Fałszywe minima prędkości (silniejsze wygładzanie, reguła „bez hamowania przed minimum”); nachodzące zakręty |
| S-04 | 26.10 | Pakiet 2026, Monza | OK | Format 2026: 24 auta, Car Telemetry 2, nowe pola Session; wszystko w jednym kodzie |
| S-05 | 26.10 | Monza, pierwszy test głosu | BŁĄD | Trenera nie słychać: winsound nie obsługuje SND_MEMORY z SND_ASYNC. Naprawa: odtwarzanie synchroniczne w wątku |
| S-06 | 26.10 | Monza, test głosu 2 | CZĘŚCIOWO | Za cicho, za rzadko, aktywacja dopiero po 2 okrążeniach mimo referencji. Naprawa: głośniejsze klipy, `--volume`, progi 0,5→0,3 s, komunikaty „referencja wczytana” i „okrążenie wyjazdowe” |
| S-07 | 26.10 | Monza, test głosu 3 | CZĘŚCIOWO | Mechanik mówił co innego niż zapis w konsoli. Naprawa: konsola i głos z jednego źródła tekstu; ocena zakrętu czeka na pełny gaz do 150 m |
| S-08 | 27.10 | Monza, partia 1 (5 okr.) | BŁĄD | Tylko powitanie przez całą sesję. Replay i symulacja na żywo: 17 komunikatów, kod poprawny. Przyczyna: pliki torów nie były w repozytorium (reguła `data/` w .gitignore), świeży klon bez nich. Naprawa: pliki dodane, test regresji A-20, dziennik `boxbox.log`, błędy wątku widoczne na nakładce |
| S-09 | 27.10 | Monza, próbna jazda po naprawie | OK | Trener mówi; gracz: „wygląda nieźle”. Pełny protokół do wykonania |

Wnioski z sesji: większość błędów „na żywo” nie była w logice trenera, tylko w otoczeniu (dźwięk w Windows,
głośność, brak plików w klonie). Dlatego od S-08 każda sesja zostawia dziennik `data/boxbox.log`, a
przypadek „trener milczy” ma od razu trzy ślady: dziennik, czerwony napis na nakładce i linię
„trener nie wystartował” w podsumowaniu.

## 6. Przypadki testowe na żywo (do wykonania, partia 1)

Każdy przypadek: kroki, oczekiwany wynik, kryterium zaliczenia. Status wpisuje gracz w formularzu.

| ID | Przypadek | Kroki i oczekiwany wynik | Status |
| --- | --- | --- | --- |
| L-01 | Start i powitanie | `trener.bat monza partia1` z folderu repo, gra w oknie bez ramki. Oczekiwane: liczba klipów w terminalu, powitanie słyszalne przed wyjazdem, nakładka w rogu ekranu | do wykonania |
| L-02 | Okrążenie wyjazdowe | Wyjazd z pit lane. Oczekiwane: „Okrążenie wyjazdowe, rozgrzej opony”, brak ocen zakrętów na tym okrążeniu | do wykonania |
| L-03 | Referencja | Pierwsze pełne okrążenie bez referencji w bazie. Oczekiwane: „Pierwsze okrążenie zapisane jako odniesienie”. Przy kolejnej sesji na tym torze: „Mam twoje najlepsze okrążenie z poprzednich sesji” | do wykonania |
| L-04 | Komunikat po zakręcie | Celowo za późne hamowanie w T1 (Monza). Oczekiwane: komunikat o T1 w ciągu ok. 2 s od wyjścia, treść zgodna z terminalem i nakładką, metry zaokrąglone do 10 | do wykonania |
| L-05 | Gaz za wcześnie | W Lesmo wcisnąć pełny gaz w apeksie. Oczekiwane: „gaz za wcześnie na wyjściu” lub „koła ślizgają się” (bez TC) | do wykonania |
| L-06 | Hamulec puszczony naraz | Przed Ascari zahamować mocno i puścić pedał w połowie. Oczekiwane: „hamulec puszczony naraz przed …” | do wykonania |
| L-07 | Czyste okrążenie | Okrążenie bez błędów. Oczekiwane: „Czyste okrążenie, pierwsze z trzech” lub „najwięcej do zyskania: …”; bez uwag o zakrętach | do wykonania |
| L-08 | Podsumowanie okrążenia | Po okrążeniu z 2–3 błędami. Oczekiwane: „Podsumowanie okrążenia” i maksymalnie 3 uwagi od największej straty | do wykonania |
| L-09 | Okrążenie nieważne | Wyjazd poza tor. Oczekiwane: „Okrążenie nieważne, wyjazd poza tor”, okrążenie nie zostaje referencją | do wykonania |
| L-10 | Nowe najlepsze | Poprawa czasu referencji. Oczekiwane: „Nowe najlepsze okrążenie”, referencja podmieniona (kolejne uwagi liczone do nowego) | do wykonania |
| L-11 | Seria i krok asyst | 3 czyste okrążenia z rzędu. Oczekiwane: komunikat o kolejnym kroku (np. TC wyłączona), linia „Cel” na nakładce 3/3, `postep.bat` pokazuje osiągnięty krok | do wykonania |
| L-12 | Nacisk reguł bez TC | Suzuka TT, TC wył. Oczekiwane: częstsze uwagi o gazie na wyjściu i trakcji niż przy TC średniej | do wykonania |
| L-13 | Rada ERS | Sesja bez asysty ERS (Time Trial). Oczekiwane po okrążeniu: „za dużo baterii w zakrętach” lub „bateria na mecie prawie pełna”, tylko gdy jest co radzić | do wykonania |
| L-14 | Nakładka | Z fotela czytelne: numer okrążenia, zakręt z metrami, 3 ostatnie komunikaty, „Cel”, „Na tym okrążeniu popraw”. Brak spadku płynności gry | do wykonania |
| L-15 | Zakończenie sesji | Esc na nakładce. Oczekiwane: tabela zakrętów z Δ, „Trener:” pod okrążeniami, „Obciążenie: X%”, ekran postępu, plik `data/boxbox.sqlite` i `data/boxbox.log` | do wykonania |
| L-16 | Ctrl+C | Zakończenie Ctrl+C w terminalu zamiast Esc. Oczekiwane: to samo co L-15 | do wykonania |
| L-17 | Obciążenie | Odczyt linii „Obciążenie”. Kryterium: poniżej 10% jednego rdzenia | do wykonania |
| L-18 | Głośność | Mechanik słyszalny na tle silnika przy VOLUME=1.5, bez przesteru | do wykonania |
| L-19 | Druga sesja na tym samym torze | Ponowne `trener.bat`. Oczekiwane: referencja z bazy od razu („Mam twoje najlepsze…”), uwagi już od pierwszego pełnego okrążenia | do wykonania |
| L-20 | Format 2026 | Ta sama sesja z UDP Format 2026. Oczekiwane: identyczne zachowanie, w podsumowaniu „format pakietów → 2026” | do wykonania |
| L-21 | Port zajęty | Uruchomić `nakladka.bat` i `trener.bat` naraz. Oczekiwane: drugi program pokazuje czerwony napis o porcie i kończy, nie zawiesza się | do wykonania |
| L-22 | Brak telemetrii | `trener.bat` bez włączonej telemetrii w grze. Oczekiwane: „czekam na telemetrię z gry” na nakładce, po Esc „brak danych” | do wykonania |

## 7. Kryteria zaliczenia partii 1

- L-01 do L-10 i L-14 do L-18 zaliczone w sesji Monza.
- L-11 do L-13 zaliczone w sesji Suzuka (lub wyraźnie opisane, dlaczego nie wystąpiły).
- Obciążenie poniżej 10%, opóźnienie komunikatu po zakręcie do ok. 2 s.
- Brak wpisów ERROR w `data/boxbox.log`.
- Gracz ocenia trafność i częstotliwość uwag na co najmniej 3/5.

Po zaliczeniu: kryterium ukończenia etapu 4 („trener mówi na czas i zrozumiale”) i etapu 5 („aplikacja
pokazuje postęp i proponuje kolejny krok”) zostają odhaczone w PLAN.md.

## 8. Zgłaszanie wyników

Po każdej sesji w folderze repo:

```
tools\package\spakuj.bat recordings\<plik>.bin
git add recordings
git add -f data\boxbox.sqlite data\boxbox.log
git commit -m "nagrania partii 1"
git push origin claude/new-session-t6gmj8
```

Do tego wypełniony formularz (poniżej) jako `recordings\<nazwa>-test.txt` albo wklejony na czacie.

## 9. Formularz na jedną sesję

```
=== TEST SESJI ===
Nazwa nagrania (z recordings\):
Tor / tryb (trening, Time Trial):
Asysty (skrzynia / TC / ABS):
Liczba okrążeń:
Jak zakończona (Esc / Ctrl+C):
Obciążenie (linia z terminala):

GŁOS
Powitanie na starcie (tak/nie):
Głośność na tle gry (za cicho / OK / za głośno):
Jakość (naturalny / sztuczny / przekręcone słowa, jakie):
Komunikat po zakręcie przychodził (od razu / z opóźnieniem ok. __ s / w następnym zakręcie):
Komunikaty za częste (które):
Komunikatów brakowało (gdzie, co się działo):
Komunikat niezgodny z tym, co zrobiłem (który, co było naprawdę):

NAKŁADKA
Widoczna i czytelna z fotela (tak/nie, co poprawić):
Numer okrążenia i zakręt z metrami zgadzały się z torem (tak/nie):
Linia "Cel" i "Na tym okrążeniu popraw" (przydatne / zbędne / nie było):
Spadek płynności gry z nakładką (tak/nie):

PO SESJI
Tabela w terminalu (była / błąd / nic):
Wynik postep.bat (krok, czyste z rzędu, zakręty opanowane):
Postęp zgadza się z tym, jak jechałem (tak/nie, dlaczego):

OCENA 1-5 (1 = przeszkadza, 5 = pomaga)
Trafność uwag:
Częstotliwość:
Ton i brzmienie:
Nakładka:

Uwagi / pomysły:
```
