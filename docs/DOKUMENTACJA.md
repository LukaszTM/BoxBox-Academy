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
| Projekt | klon repozytorium projektu (GitHub), gałąź `claude/new-session-t6gmj8`, praca z katalogu głównego |

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
| `recorder.bat [nazwa]` | Recorder kształtu toru: nagrywa sesję z pakietem Motion, liczy realny kształt toru i pakuje wszystko do `recorder\*.zip` |
| `zbuduj_recorder.bat` | Buduje `dist\BoxBoxRecorder.exe` (PyInstaller, jeden plik, bez Pythona u odbiorcy) |

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
| `--guidance on/off` | prowadzenie w nieopanowanych zakrętach: puść gaz, hamuj (jak mocno), pół gazu, pełny gaz |
| `--skills` | profil umiejętności 0–100 na każdym torze (hamowanie, praca hamulcem, gaz, powtarzalność, tempo, samodzielność) i wyjdź; wzory: `coach/skills.py`, wytyczne zakładki: `docs/ANALIZA_UMIEJETNOSCI.md`; w oknie zakładka Umiejętności |
| `--badges` | odznaki (12, z celem i postępem) i trzy cele dnia z bazy; `coach/badges.py`; te same odznaki na stronie Postęp w oknie |

Raport PDF sesji: na podsumowaniu sesji przycisk „Zapisz raport PDF” zapisuje `data\raporty\raport-<tor>-<data>.pdf`
(radar umiejętności z poprzednim oknem, sześć wskazówek, zadanie na następną sesję, „Dobrze / Do pracy”, tabela
okrążeń i zakrętów referencji). Strona HTML (`gui/report.py`) jest drukowana do PDF przez Qt bez okna dialogowego.
„Drukuj” nadal otwiera systemowe okno drukowania (jedyny wyjątek od zasady „bez osobnych okien”).
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
(powrót do pełnego gazu). W pakiecie są: Bahrajn (3), Monza (11), Suzuka (13). Nowy tor robi się jednym
poleceniem z nagrania (`python -m boxbox.tracks.detect <nagranie> --car pb`), które szuka minimów
prędkości potwierdzonych hamowaniem, łączy zakręty bez pełnego gazu między nimi i przycina nachodzące strefy.

**Tor bez pliku (pozostałe tory F1 25 i 2026 Season Pack):** sesja działa od razu. Trener czeka na
pierwsze pełne okrążenie, wyznacza z niego zakręty tym samym algorytmem (`boxbox/tracks/auto.py`),
nazywa je T1..Tn według kolejności stref hamowania (szykana to jedna strefa, więc numeracja może różnić
się od gry), zapisuje `data\tracks\<id>.json` i startuje; to okrążenie zostaje referencją. W kolejnych
sesjach plik jest wczytywany od razu; można w nim poprawić nazwy i granice. Plik wbudowany
w `boxbox\tracks\data\` ma zawsze pierwszeństwo (`find_track_path`). Gdy z trzech pełnych okrążeń
nie da się wyznaczyć zakrętów (mniej niż 3 strefy hamowania), trener wyłącza się z komunikatem.

Przewodnik `guide\<id>.json` to lżejsza lista „nazwa + apeks + notatka” dla nakładki; po pierwszym
pełnym okrążeniu nakładka kalibruje go do stref hamowania gracza. Tor bez przewodnika dostaje go
z pliku toru (`guide_from_track`), więc nakładka HUD pokazuje zbliżający się zakręt na każdym torze.

### Realny kształt toru (recorder)

`python -m boxbox.recorder` (albo `BoxBoxRecorder.exe`) nagrywa sesję razem z pakietem Motion
(pozycja auta w świecie gry, pomijanym w zwykłych nagraniach), łączy pozycję z dystansem okrążenia
i z najlepszego pełnego okrążenia zapisuje `boxbox\tracks\shape\<id>.json`: punkt co 10 m plus
pozycje apeksów z pliku toru, oraz SVG z obrysem, metą i numerami zakrętów. Na koniec pakuje do
`recorder\nagranie-<tor>-<data>.zip` wszystko, co potrzebne do pracy nad torem: nagranie `.bin.xz`,
kształt, plik toru i przewodnik, bazę i dziennik z `data\`, podsumowanie z liczbami pakietów.
ZIP ponad 24 MB jest dzielony na części. Kształt posłuży do mapy toru na nakładce i do
sprawdzania, czy zakręty z pliku toru leżą tam, gdzie w grze.

## 6. Okrążenia, metryki i referencja

`LapRecorder` zbiera próbki (dystans, prędkość, gaz, hamulec, bieg, czas) i zamyka okrążenie przy
zmianie numeru. Okrążenie ma czas, flagi ważne/pit/pełne, asysty wybrane głosowaniem z próbek
(gra potrafi zmieniać je w trakcie), próbki ERS, DRS i opon oraz czasy sektorów: S1 i S2 z Lap Data
w trakcie okrążenia, S3 = czas okrążenia minus S1 i S2 po mecie (bez kompletu sektory zostają puste).

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

### Prowadzenie w zakręcie (`coach/guide_live.py`)

W zakrętach, które gracz ma nieopanowane, trener nie czeka z uwagą na wyjście, tylko prowadzi przed
punktem: „Zakręt czwarty. Prowadzę.” ok. 220 m przed pierwszą komendą, potem „Puść gaz.”, „Mocny
hamulec / Pół hamulca / Lekki hamulec.” (według maksymalnego hamulca referencji: od 80 %, od 45 %, poniżej),
„Pół gazu.” w apeksie (gdy referencja daje pełny gaz dopiero 40 m dalej) i „Pełny gaz.”. Punkty
pochodzą z okrążenia referencyjnego (`CornerMetrics`: `lift_m`, `brake_point_m`, `max_brake`,
`apex_m`, `full_throttle_m`); komenda pada o 1 s jazdy wcześniej (prędkość × 1 s, min. 15 m),
żeby wybrzmiała dokładnie w punkcie, i przerywa to, co właśnie leci (pilna). Zakręty do prowadzenia
(najwyżej 3): te z uwagami z podsumowania ostatniego okrążenia, a na starcie sesji te z uwagami
z poprzednich sesji w bazie; zakręt bez uwagi wypada z listy sam. Lekcja z jednym zakrętem
prowadzi tylko ten zakręt. Wyłączenie: `--guidance off`. Klipy `guide_*` w katalogu fraz
(do dogrania tym samym skryptem co reszta; bez klipu komenda jest tylko w tekście na nakładce).

### Sektory i polecenie na następne okrążenie

`coach/sectors.py`: po ważnym okrążeniu trener mówi, w którym sektorze gracz traci najwięcej do swoich
najlepszych sektorów z tej sesji („Najwięcej tracisz w drugim sektorze, około pół sekundy.”; kubełki
0,2 / 0,3 / 0,5 / 0,8 / 1 / 1,5 / 2 / ponad 3 s, poniżej 0,2 s cicho), a do najważniejszej uwagi z metrami
dokłada polecenie: „Na następnym okrążeniu zacznij hamować wcześniej, o jakieś dwadzieścia metrów”
(połowa różnicy, 5–20 m, jak cel na nakładce). Panel na żywo pokazuje S1–S3 bieżącego okrążenia z różnicą
do najlepszych sektorów sesji, podsumowanie sesji zdanie o sektorach najlepszego okrążenia.

### DRS i opony po okrążeniu

`coach/drs.py`: strefy DRS z telemetrii (lampka `drsAllowed` z Car Status, skrzydło z Car Telemetry), czas reakcji
i metry straty w każdej strefie, strefa pominięta. Po ważnym okrążeniu jedna rada: „nie włączyłeś DRS na prostej”
albo „DRS włączony za późno” (reakcja ponad 0,5 s; zwykła z nagrań to 20–40 ms). Z asystą DRS gra włącza sama,
więc trener milczy. `coach/tyres.py`: próbki opon co 25 m, raport na okrążenie (średnie temperatury powierzchni
i wnętrza kół, zużycie na okrążenie, prognoza okrążeń do 70 % zużycia) i rada raz na sesję: tył albo przód grzeje
się bardziej (różnica 12 °C), jedna strona dużo cieplejsza (15 °C), zużycie powyżej 4 % na okrążenie, jedno koło
zużyte o 8 % bardziej. Progi względne, bo okno temperatur zależy od mieszanki; do sprawdzenia na żywo.

## 8a. Lekcje, tryb „wytłumacz mi”, podsumowanie sesji

`coach/lessons.py`: siedem lekcji (cztery darmowe: hamowanie w jednym zakręcie, gaz na wyjściu, czyste
okrążenie, trail-braking; trzy premium: bateria na prostych, DRS w każdej strefie, opony w oknie), każda
z regułami, o których trener mówi, i warunkiem zaliczenia: seria okrążeń bez danej uwagi albo, w lekcjach
DRS/baterii/opon, seria okrążeń spełniających cel liczony z danych okrążenia (DRS w każdej strefie
do 0,5 s po lampce i bez asysty DRS; mniej niż 25 % deployu w zakrętach i poniżej 90 % baterii na mecie
bez asysty ERS; brak rady o oponach po okrążeniu). `--lesson <id> [--lesson-corner N]` w konsoli;
po sesji wynik „zaliczona / najlepsza seria n/3”. `coach/glossary.py`: słownik pojęć i dłuższe wersje
uwag; `--explain` dokłada wyjaśnienie przy pierwszej uwadze danego typu (klipy `explain_*` w katalogu
fraz). `coach/summary.py`: po sesji jedno zdanie „Dobrze” (nowe najlepsze, hamowanie później niż
w poprzednich sesjach, czyste okrążenia) i jedno „Do pracy” (zakręt z największą stratą, reguła po
polsku). `coach/delta.py`: delta czasu do referencji co 10 m, odcinki największych strat, CSV okrążenia.
`games/`: adapter gry (F1 25) z nazwami asyst i formatami; baza i pliki torów mają pole gry, żeby
kolejne gry nie zmieniały okna. `tools/bugreport.py`: raport błędu ZIP.

## 8b. Inżynier na radiu (tryb wyścigowy)

`engineer/rules.py`: klasa `Engineer` dostaje kolejne stany telemetrii i mówi tylko o zmianach, z
czasami wyciszenia per komunikat. Reaguje na: światła startowe i zgaszenie, flagi FIA (żółta, niebieska,
czerwona, koniec żółtej), safety car i VSC (ze zdarzeń i ze stanu sesji), DRS włączony/wyłączony,
okno pit-stopu (idealne i ostatnie okrążenie), ostatnie 3 okrążenia i ostatnie okrążenie, zmiany
pozycji, odstęp do auta z przodu i z tyłu (w zasięgu DRS / bezpieczny / w sekundach), ostrzeżenia
i kary czasowe, zużycie opon (przód/tył 60 %, krytyczne 85 %, reset po pit-stopie), uszkodzenia
skrzydeł, podłogi, silnika, przebicie, paliwo (oszczędzaj / możesz cisnąć), deszcz i schnięcie toru,
kolizje z udziałem gracza, meta. `engineer/start.py`: po zgaszeniu świateł zbiera 5 s gazu,
prędkości i obrotów; po pierwszym okrążeniu raport: czas reakcji, uślizg, pozycje. Uruchomienie:
`python -m boxbox.app --mode race` (okno: po makiecie v2).

## 9. Postęp i ERS

Kroki: 1 automat/TC pełna/ABS, 2 TC średnia, 3 TC wyłączona, 4 ABS wyłączony. Okrążenie czyste:
ważne, bez pit, z czasem, bez komunikatu o wadze ≥ 1 s. Trzy czyste z rzędu → komunikat o kolejnym
kroku i zapis w tabeli `progress`. Zmiana asyst zmienia krok i zeruje serię. Ekran `--progress`:
tor, krok, seria, osiągnięte kroki, najlepszy czas na każdym kroku, zakręty bez uwag w ostatnich 3
ważnych okrążeniach (opanowane) i zakręty do pracy z nazwami reguł.

Zakładka Postęp w oknie dokłada: sumę najlepszych sektorów (teoretyczne najlepsze okrążenie), spójność
jazdy (`coach/consistency.py`: odchylenie czasów z ostatnich 10 ważnych okrążeń; względem średniego czasu
do 0,5 % „bardzo równo”, 1 % „równo”, 2 % „zmiennie”, wyżej „nierówno”, każda ocena z jedną radą), odsetek
czystych okrążeń toru oraz „Wtedy vs dziś”: sesje sprzed co najmniej 4 tygodni kontra ostatni tydzień
(bez tak starych danych: pierwszy dzień jazdy kontra ostatni), w tabeli okrążenia, najlepszy i średni czas,
odsetek czystych, pod nią zdanie podsumowania. Historia przejazdów ma kolumny S1–S3 z najlepszym sektorem
wyróżnionym. Zakładka Analiza: referencją może być najlepsze okrążenie toru, poprzednie albo dowolne
z sesji; poza prędkością, pedałami, biegiem i kierownicą wykres DRS (z liczbą włączonych stref) i baterii
ERS 0–4 MJ, a na mapie toru strefy DRS z okrążenia (zielone włączone, bursztynowe pominięte). Eksport CSV
okrążenia dokłada kolumny `drs` (0/1) i `bateria_mj`, gdy okrążenie ma te kanały.

ERS: deploy liczony per strefa z próbek baterii; ponad 25% deployu w strefach hamowania → „za dużo
baterii w zakrętach”; bateria na mecie powyżej 90% → „bateria prawie pełna”. Przy włączonej asyście ERS rady nie ma.

Plan baterii (`coach/ers_plan.py`): proste między zakrętami z czasem przejazdu z okrążenia referencyjnego,
uszeregowane od najdłuższej; deploy dostają te, które mieszczą się w budżecie ok. 33 s pełnej mocy (4 MJ przy
120 kW). Na żywo 250 m przed najdłuższą prostą przy baterii poniżej 15 %: „bateria prawie pusta, a zaraz
najdłuższa prosta”; po okrążeniu, gdy mniej niż 70 % deployu poszło na zaplanowane proste: „bateria idzie
w złych miejscach”. Plan odnawia się z każdą nową referencją; `describe(plan)` daje zdanie do okna.

## 10. Głos

Katalog 710 fraz (`assets\voice\phrases.csv`, generowany z kodu): klipy zakrętów `corner_t1`…
i kombinacje z plików torów, reguły w dwóch częściach (`rule_<r>_a/_b`), liczby metrów `num_10…300`,
biegi, komunikaty ogólne `misc_*`, pełne zdania `v2_<reguła>_<zakręt>[_metry]` z poprawną
odmianą („w zakręcie czwartym”, „przed zakrętami od ósmego do dziesiątego”), inżynier `eng_*`
(opony, pit, flagi, odstępy, uszkodzenia, pogoda, liczby okrążeń, sekundy, pozycje), komendy
prowadzenia w zakręcie `guide_*` (7 krótkich: „Prowadzę.”, „Puść gaz.”, „Mocny hamulec.”, „Pół
hamulca.”, „Lekki hamulec.”, „Pół gazu.”, „Pełny gaz.”), DRS i opony `misc_drs_*`, `misc_tyres_*`.

Generowanie raz, offline: ElevenLabs, głos „Piotr”, model multilingual v2, stability 0,36,
similarity 0,68, PCM 22 050 Hz mono. Klucz API tylko w zmiennej środowiskowej, nigdy w plikach.
Znana wada głosu: końcówkę „-uj” czyta jako „-uć”, dlatego zdania są pisane bez niej.
Lektor samouczka: klipy `tutorial_0`–`tutorial_6` (po jednym na krok samouczka w oknie); gdy są w bibliotece,
mechanik czyta krok przy jego otwarciu, bez klipów dymek zostaje tylko tekstem.

Efekt radia (`boxbox.voice.radio`): dwa filtry górnoprzepustowe 300 Hz, dwa dolnoprzepustowe 3400 Hz,
miękkie ograniczenie (drive 4,5), szczyt 0,98, szum −48 dB, klik PTT, przycięcie ciszy. Odtwarzacz
składa klipy z 120 ms przerwy, kolejka 3 komunikatów, głośność z `--volume`, winsound synchronicznie w wątku.

## 11. Baza danych

SQLite `data\boxbox.sqlite`: `sessions` (uid gry jako tekst, źródło, tor, format), `laps` (numer, czas,
ważne, pełne, pit, skrzynia, TC, ABS, sektory S1–S3), `corner_metrics` (wszystkie metryki z p. 6), `lap_samples`
(próbki w blobie), `lap_channels` (próbki DRS i ERS okrążenia w blobach, do wykresów i CSV),
`lap_messages` (zakręt, reguła, waga), `progress` (krok, seria, osiągnięte).
Migracje dodają brakujące kolumny przy starcie. Obok bazy dziennik `boxbox.log`: start, cwd, wersja
Pythona, start trenera i tor, każdy komunikat z czasem, każde okrążenie, błędy wątków, obciążenie.

Scena na Starcie: obrys ostatnio jeżdżonego toru (domyślnie Monza) z pięcioma kolorowymi kropkami-bolidami
animowanymi w SVG (`animateMotion`), bez JavaScriptu; w trakcie sesji kropki stoją. Strona podmienia tylko
zmienione węzły DOM przy odświeżeniu stanu, więc obrazy i animacje nie migają.

## 12. Nakładki

Nakładka trenera (`--overlay`): okno zawsze na wierzchu, bez ramki, przeciągane, Esc kończy sesję.
Pokazuje: OKRĄŻENIE N (pit/nieważne), najbliższy zakręt z metrami lub TERAZ, żółte „Na tym
okrążeniu popraw: …” po każdym okrążeniu, trzy ostatnie komunikaty mechanika, zielone
„Cel: 3 czyste okrążenia z rzędu (n/3), potem: …”, pasek stanu (prędkość, bieg, dystans, nagrywanie),
czerwony komunikat o błędzie portu lub wątku. Gra musi być w trybie okna bez ramki.

Nakładka HUD (zakładka HUD F1, `gui/hud.py` + `web/hud.html`): osiem modułów przeciąganych w edytorze
(stan, zakręt, cel, delta, DRS · bateria · sektory, radio, minimapa, plansza po okrążeniu). Moduł
DRS · bateria · sektory pokazuje lampkę i skrzydło DRS (GOTOWY / OTWARTY), baterię w procentach z paskiem
oraz S1 i S2 bieżącego okrążenia; sektor lepszy od najlepszego z sesji jest fioletowy.

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
