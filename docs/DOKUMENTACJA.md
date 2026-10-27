# BoxBox Academy – dokumentacja aplikacji

Wersja z 27.10.2026 (po etapach 0–5). Aplikacja PC w Pythonie, która odbiera telemetrię UDP z F1 25
i mówi do gracza głosem mechanika-instruktora. Tryb nauki jest gotowy; tryb wyścigowy (inżynier na
radiu) ma przygotowane teksty klipów i czeka na etap 6.

## 1. Do czego służy

Gracz jedzie w F1 25, a aplikacja w tle:

1. odbiera pakiety telemetrii z gry (port UDP 20777, 60 razy na sekundę),
2. dzieli jazdę na okrążenia i zakręty według pliku toru,
3. porównuje każdy zakręt z okrążeniem referencyjnym (własne najlepsze z bazy, pierwsze pełne w sesji albo duch z Time Trial),
4. po wyjściu z zakrętu mówi jedną konkretną uwagę („Zakręt pierwszy. Hamowanie za późno, o jakieś pięćdziesiąt metrów”), a po okrążeniu podsumowanie z maksymalnie trzema uwagami,
5. prowadzi gracza przez zdejmowanie asyst: automat i pełna kontrola trakcji → TC średnia → TC wyłączona → ABS wyłączony, krok po 3 czystych okrążeniach z rzędu,
6. zapisuje okrążenia, metryki i postęp w bazie SQLite i pokazuje ekran postępu,
7. opcjonalnie wyświetla nakładkę na grę z okrążeniem, najbliższym zakrętem, ostatnimi komunikatami, celem i tym, co poprawić.

Ton komunikatów: spokojny instruktor, konkretnie, bez krzyku. Komunikaty po polsku, kod po angielsku.

## 2. Wymagania i uruchomienie

| Element | Wymaganie |
| --- | --- |
| System | Windows 10/11 (dźwięk przez winsound, nakładka przez tkinter); Linux/macOS: konsola i replay, dźwięk przez `aplay`/`afplay` |
| Python | 3.12 lub nowszy, z tkinter (instalator z python.org). Bez dodatkowych bibliotek w aplikacji |
| Gra | F1 25, Ustawienia → Telemetria: UDP wł., broadcast wył., IP 127.0.0.1, port 20777, 60 Hz, format 2025 lub 2026, „Twoja telemetria: publiczna”; tryb okna bez ramki przy nakładce |
| Projekt | klon repozytorium `projekt (GitHub)`, gałąź `claude/new-session-t6gmj8`, praca z katalogu głównego |

Skrypty `.bat` w `tools\package\` (działają z klonu i z paczki ZIP):

| Skrypt | Co robi |
| --- | --- |
| `trener.bat <nazwa>` | Trener na żywo z głosem i nakładką, nagrywa sesję do `recordings\`, po Esc/Ctrl+C tabela, postęp, obciążenie. Zmienne na górze pliku: `VOLUME` (1.5), `NAKLADKA` (1/0), `SKALA` |
| `postep.bat` | Ekran postępu z bazy: krok asyst, seria, najlepsze czasy per krok, zakręty opanowane i do pracy |
| `glos-test.bat` | Test głośników bez gry: powitanie i przykładowy komunikat |
| `nakladka.bat <nazwa>` | Nakładka do nagrań według planu sesji (`plany\*.json`) + nagrywanie, bez trenera |
| `nagraj.bat <nazwa>` | Samo nagrywanie telemetrii |
| `sprawdz.bat <plik>` | Podsumowanie nagrania: liczby pakietów, format, błędy |
| `spakuj.bat <plik lub folder>` | xz i podział na części po 20 MB (limit GitHuba 25 MB); folder → tar.xz |
| `wygeneruj_glos.bat` | Generowanie brakujących klipów przez ElevenLabs (klucz wpisywany bez echa) i efekt radia |
| `popraw_glos.bat` | Ponowne wygenerowanie 8 zdań, które zmieniły brzmienie |

Linia poleceń (`py -3 -m boxbox.app ...`):

| Opcja | Znaczenie |
| --- | --- |
| `--mode coach` / `race` | tryb nauki (domyślny) / wyścigowy (etap 6) |
| `--replay <plik>` `--speed N` | odtworzenie nagrania zamiast gry; 0 = bez czekania |
| `--port`, `--duration` | port UDP, limit nasłuchu w sekundach |
| `--track <json>` | plik toru zamiast automatycznego po id z gry |
| `--db <plik>` | baza SQLite (domyślnie `data\boxbox.sqlite`); dziennik `boxbox.log` obok niej |
| `--reference best/rival/pb` | referencja: własne najlepsze / duch rywala / własny duch (replay) |
| `--record <nazwa>` | nagrywanie sesji na żywo do `recordings\` |
| `--voice <folder>`, `--no-voice`, `--volume` | klipy głosu, wyłączenie dźwięku, wzmocnienie |
| `--corner-messages on/off` | krótki komunikat tuż po zakręcie |
| `--overlay`, `--scale`, `--alpha` | nakładka trenera, skala napisów, krycie |
| `--progress` | ekran postępu i wyjście |

## 3. Architektura

Pakiet `boxbox/`, warstwy od dołu:

| Moduł | Odpowiedzialność |
| --- | --- |
| `telemetry/` | Nagłówek i parsery pakietów F1 25 (2025 i 2026), stan telemetrii, nasłuch UDP, zapis i odtwarzanie nagrań |
| `tracks/` | Model toru (zakręty z metrami wejścia, apeksu, wyjścia), wykrywanie zakrętów z nagrań, pliki `data\<id>.json` i przewodniki `guide\<id>.json` |
| `coach/` | Okrążenia i próbki, metryki zakrętów, porównanie z referencją, reguły, trener na żywo, ERS, postęp, raport po sesji. Nie dotyka UI ani dźwięku: zwraca listę komunikatów |
| `engineer/` | Teksty inżyniera na radiu (etap 6) |
| `voice/` | Katalog fraz, efekt radia, odtwarzacz klipów |
| `storage/` | Baza SQLite |
| `ui/` | Konsola, nakładka do nagrań, nakładka trenera, model widoków |
| `tools/` | Pakowanie nagrań |
| `app.py` | Spięcie warstw, argumenty, wątki, dziennik |

Przepływ danych na żywo: `udp.listen` → `LapRecorder.feed` (stan + okrążenia) → `LiveCoach.update`
(metryki, reguły) → `speak(ids, text)` → konsola, nakładka, `VoicePlayer`. Z `--overlay` telemetria
chodzi w wątku roboczym, a okno tkinter w wątku głównym; dzielą stan pod blokadą (`SharedCoachState`).
Po sesji `report_laps` zapisuje okrążenia do bazy i drukuje tabelę.

## 4. Telemetria

Obsługiwane formaty: 2025 (22 auta) i 2026 Season Pack (24 auta, dodatkowy pakiet Car Telemetry 2,
rozszerzony Session). Format jest brany z nagłówka każdego pakietu, więc oba działają jednym kodem.
Rozmiary struktur zweryfikowane ze specyfikacją EA (pliki w `docs/`) i pięcioma nagraniami z gry.

Parsowane pakiety: Session (tor, długość, typ sesji, asysty, pogoda, strefy DRS, SC), Lap Data
(dystans, czasy, numer okrążenia, pit, nieważne), Car Telemetry (prędkość, gaz, hamulec, bieg,
kierownica, temperatury), Car Status (TC, ABS, ERS, paliwo, opony), Car Damage, Event (start,
flagi, kolizje, kary), Participants, Time Trial, Car Telemetry 2 (2026). Dane innych aut są
parsowane leniwie, dopiero gdy ktoś o nie zapyta (10× szybsze testy i mniejsze obciążenie).

Nagranie: plik `BBXREC01`, rekordy `<czas double, długość uint16, dane>`, kompresja xz, bez pakietów
Motion, Car Setup, Final Classification, Lobby, Motion Ex, Lap Positions (zbędne, duże).

## 5. Tor i zakręty

Plik toru `boxbox\tracks\data\<track_id>.json`: lista zakrętów z numerem, nazwą jak w grze (`T1`,
`T4-T5`, `T8-T10`), metrami wejścia (początek hamowania), apeksu (minimum prędkości) i wyjścia
(powrót do pełnego gazu). Są: Bahrajn (3), Monza (11), Suzuka (13). Nowy tor robi się jednym
poleceniem z nagrania (`python -m boxbox.tracks.detect <nagranie> --car pb`), które szuka minimów
prędkości potwierdzonych hamowaniem, łączy zakręty bez pełnego gazu między nimi i przycina nachodzące strefy.

Przewodnik `guide\<id>.json` to lżejsza lista „nazwa + apeks + notatka” dla nakładki; po pierwszym
pełnym okrążeniu nakładka kalibruje go do stref hamowania gracza.

## 6. Okrążenia, metryki i referencja

`LapRecorder` zbiera próbki (dystans, prędkość, gaz, hamulec, bieg, czas) i zamyka okrążenie przy
zmianie numeru. Okrążenie ma czas, flagi ważne/pit/pełne, asysty wybrane głosowaniem z próbek
(gra potrafi zmieniać je w trakcie) i próbki ERS.

Dla każdego zakrętu liczone są: v_min i jej miejsce (środek plateau), bieg w apeksie, prędkość
wejścia i wyjścia, czas przejazdu strefy, punkt hamowania, koniec hamowania, czas puszczania
hamulca, maksymalny hamulec, punkt pełnego gazu. Referencja: najlepsze ważne okrążenie z bazy dla
toru; bez niej pierwsze pełne okrążenie sesji; w replayu także duch rywala z Time Trial (prędkość
ducha liczona z dystansu i czasu, bo pole z gry jest błędne).

## 7. Reguły trenera

Każda reguła zwraca komunikat z wagą równą szacowanej stracie czasu. Trener mówi, gdy strata w
zakręcie przekracza 0,3 s; na czystym okrążeniu podpowiada „najwięcej do zyskania” od 0,15 s.
Po okrążeniu wybiera 3 najcięższe.

| Reguła | Warunek (względem referencji) |
| --- | --- |
| Hamowanie za późno | punkt hamowania późniejszy o ponad 20 m; wariant „dużo za późno”, gdy v_min spadła wyraźnie |
| Hamowanie za wcześnie | wcześniejszy o ponad 25 m przy zapasie prędkości w apeksie |
| Hamulec puszczony naraz | czas puszczania poniżej 0,25 s, gdy referencja puszcza ponad 0,4 s |
| Brak trail-brakingu | hamowanie kończy się ponad 40 m przed apeksem wcześniej niż u referencji |
| Pełny gaz za późno | o ponad 30 m |
| Gaz za wcześnie | o ponad 25 m z utratą prędkości wyjścia |
| Utrata przyczepności | v_min poniżej 60% referencji (obrót, żwir); wariant „na gazie” lub „na wejściu” |
| Bieg za niski / za wysoki | inny bieg w apeksie niż referencja |

Nacisk po zdjęciu asyst: bez TC waga gazu za wcześnie ×1,5 i utraty przyczepności ×1,3; bez ABS
hamowania za późno ×1,3, puszczenia hamulca ×1,5, trail-brakingu ×1,3.

## 8. Trener na żywo

Kolejność w sesji: powitanie od razu po starcie (test dźwięku), „mam twoje najlepsze okrążenie” gdy
jest referencja w bazie, „okrążenie wyjazdowe” przy wyjeździe z pit lane, komunikat o zakręcie
25–150 m za wyjściem (czeka na pełny gaz, najdalej ok. 2 s), po okrążeniu: „podsumowanie” z 1–3
uwagami, „czyste okrążenie, pierwsze z trzech”, „okrążenie nieważne”, „nowe najlepsze”, po 3
czystych z rzędu komunikat o kolejnym kroku asyst, rada ERS gdy asysta ERS wyłączona, „koniec
sesji”. Tekst w konsoli i na nakładce jest budowany z tych samych fraz co mowa, więc zawsze się zgadzają.

## 9. Postęp i ERS

Kroki: 1 automat/TC pełna/ABS, 2 TC średnia, 3 TC wyłączona, 4 ABS wyłączony. Okrążenie czyste:
ważne, bez pit, z czasem, bez komunikatu o wadze ≥ 1 s. Trzy czyste z rzędu → komunikat o kolejnym
kroku i zapis w tabeli `progress`. Zmiana asyst zmienia krok i zeruje serię. Ekran `--progress`:
tor, krok, seria, osiągnięte kroki, najlepszy czas na każdym kroku, zakręty bez uwag w ostatnich 3
ważnych okrążeniach (opanowane) i zakręty do pracy z nazwami reguł.

ERS: deploy liczony per strefa z próbek baterii; ponad 25% deployu w strefach hamowania → „za dużo
baterii w zakrętach”; bateria na mecie powyżej 90% → „bateria prawie pełna”. Przy włączonej asyście ERS rady nie ma.

## 10. Głos

Katalog 694 fraz (`assets\voice\phrases.csv`, generowany z kodu): klipy zakrętów `corner_t1`…
i kombinacje z plików torów, reguły w dwóch częściach (`rule_<r>_a/_b`), liczby metrów `num_10…300`,
biegi, komunikaty ogólne `misc_*`, pełne zdania `v2_<reguła>_<zakręt>[_metry]` z poprawną
odmianą („w zakręcie czwartym”, „przed zakrętami od ósmego do dziesiątego”), inżynier `eng_*`
(opony, pit, flagi, odstępy, uszkodzenia, pogoda, liczby okrążeń, sekundy, pozycje).

Generowanie raz, offline: ElevenLabs, głos „Piotr”, model multilingual v2, stability 0,36,
similarity 0,68, PCM 22 050 Hz mono. Klucz API tylko w zmiennej środowiskowej, nigdy w plikach.
Znana wada głosu: końcówkę „-uj” czyta jako „-uć”, dlatego zdania są pisane bez niej.

Efekt radia (`boxbox.voice.radio`): dwa filtry górnoprzepustowe 300 Hz, dwa dolnoprzepustowe 3400 Hz,
miękkie ograniczenie (drive 4,5), szczyt 0,98, szum −48 dB, klik PTT, przycięcie ciszy. Odtwarzacz
składa klipy z 120 ms przerwy, kolejka 3 komunikatów, głośność z `--volume`, winsound synchronicznie w wątku.

## 11. Baza danych

SQLite `data\boxbox.sqlite`: `sessions` (uid gry jako tekst, źródło, tor, format), `laps` (numer, czas,
ważne, pełne, pit, skrzynia, TC, ABS), `corner_metrics` (wszystkie metryki z p. 6), `lap_samples`
(próbki w blobie), `lap_messages` (zakręt, reguła, waga), `progress` (krok, seria, osiągnięte).
Migracje dodają brakujące kolumny przy starcie. Obok bazy dziennik `boxbox.log`: start, cwd, wersja
Pythona, start trenera i tor, każdy komunikat z czasem, każde okrążenie, błędy wątków, obciążenie.

## 12. Nakładki

Nakładka trenera (`--overlay`): okno zawsze na wierzchu, bez ramki, przeciągane, Esc kończy sesję.
Pokazuje: OKRĄŻENIE N (pit/nieważne), najbliższy zakręt z metrami lub TERAZ, żółte „Na tym
okrążeniu popraw: …” po każdym okrążeniu, trzy ostatnie komunikaty mechanika, zielone
„Cel: 3 czyste okrążenia z rzędu (n/3), potem: …”, pasek stanu (prędkość, bieg, dystans, nagrywanie),
czerwony komunikat o błędzie portu lub wątku. Gra musi być w trybie okna bez ramki.

Nakładka do nagrań (`nakladka.bat`): cel na okrążenie i zadanie w zakręcie z planu sesji, lista
zadań z automatycznym odhaczaniem.

## 13. Struktura katalogów

| Katalog | Zawartość |
| --- | --- |
| `boxbox\` | kod aplikacji |
| `assets\voice\` | klipy z radiem; `raw\` surowe z ElevenLabs; `phrases.csv` |
| `recordings\` | nagrania `.bin.xz`, notatki `.txt`, przewodniki `.guide.json` |
| `data\` | baza i dziennik (poza repozytorium) |
| `docs\` | instrukcja nagrań, protokół testów, ten dokument, specyfikacje EA |
| `tools\` | generator głosu, budowanie paczki, skrypty `.bat` w `package\` i plany sesji |
| `tests\` | 175 testów pytest, nagrania wzorcowe jako fixtury |

## 14. Testy i jakość

`pytest` uruchamia 175 testów w ok. 3 minuty. Każda reguła ma test na nagranym pakiecie UDP.
Nagrania z gry są fixturami, więc zmiana parsera lub reguły od razu pokazuje różnicę na
prawdziwych danych. Plan testów i przypadki na żywo: `docs\PLAN_TESTOW.md`.

## 15. Znane ograniczenia i plan

- Pliki torów są tylko dla Bahrajnu, Monzy i Suzuki; inny tor wyłącza trenera na żywo (tabela po sesji działa, zakręty da się wykryć z nagrania).
- Nakładka wymaga tkinter i gry w oknie bez ramki.
- Duch Time Trial jako referencja działa w replayu, nie na żywo.
- Etap 6: reguły inżyniera (teksty gotowe), komendy głosowe, okno wyboru trybu, `.exe` przez PyInstaller.
