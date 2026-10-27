# BoxBox Academy – plan realizacji (PC)

Oct 26, 2026 · @KIEROWCA

## Cel i zakres

BoxBox Academy to aplikacja na PC, która podłącza się do telemetrii F1 25 i mówi do gracza głosem mechanika: w trybie nauki uczy jazdy bez ułatwień, w trybie wyścigowym pełni rolę inżyniera wyścigowego. Grupa docelowa: początkujący, którzy chcą zdjąć asysty i realnie poprawić czasy.

**Tryb nauki (priorytet)**

- Prędkość i bieg w każdym zakręcie względem okrążenia referencyjnego.
- Gaz i hamulec: za późne/za wczesne hamowanie, brak trail-brakingu, za wczesny gaz na wyjściu.
- Bateria (ERS): gdzie deploy daje czas, gdzie się marnuje, stan baterii na ostatnim okrążeniu.
- Feedback po zakręcie (jedno krótkie zdanie) i po okrążeniu (2–3 najważniejsze rzeczy), nigdy w trakcie zakrętu.
- Stopniowe zdejmowanie asyst z celem na każdy krok: automat → TC średnie → TC wyłączone → ABS wyłączony. Linia jazdy zostaje.

**Tryb wyścigowy**

- Tempo rywali, zużycie opon, bateria, pit-stop, flagi, uszkodzenia.
- Reaguje na zdarzenia w wyścigu, nie poprawia techniki.

**Poza zakresem MVP** (do dopisania później): swobodna rozmowa z mechanikiem przez model językowy i klucz API, wersja mobilna, nakładka na ekranie gry (jest tylko prosta nakładka pomocnicza do nagrań: `boxbox/ui/overlay.py`, tkinter), konta użytkowników i chmura.

## Stack i architektura

Python 3.12, silnik oddzielony od interfejsu, żadnych usług w chmurze w MVP. Wszystko działa lokalnie na tym samym PC co gra albo w tej samej sieci.

| Warstwa | Technologia | Po co |
| --- | --- | --- |
| Odbiór telemetrii | socket UDP + `struct` (własny parser) lub gotowa biblioteka do pakietów F1 25 | Gra wysyła pakiety UDP (port 20777), ok. 20–60 razy na sekundę |
| Model danych | `dataclasses` / `pydantic` | Pakiety: sesja, okrążenie, telemetria auta, status auta, zdarzenia, asysty |
| Silnik trenera | czysty Python, reguły + porównanie z okrążeniem referencyjnym | Wykrywa błędy w zakrętach, liczy deploy baterii, ocenia postęp |
| Silnik wyścigowy | czysty Python, reguły na zdarzeniach | Komunikaty o oponach, pit-stopie, flagach, rywalach |
| Dane torów | pliki JSON: tor → lista zakrętów (dystans od startu okrążenia) | Mapowanie pozycji na numer zakrętu |
| Głos | gotowe klipy WAV (wygenerowane raz przez TTS) + efekt radia; odtwarzanie `sounddevice` lub `pygame.mixer` | Zero kosztów na użytkownika, działa offline |
| Komendy głosowe | lokalne rozpoznawanie mowy (np. Vosk lub whisper.cpp), ograniczony słownik komend | Pytania typu "jakie opony", "ile baterii", "jak ostatni sektor" |
| Interfejs | okno w `PySide6` lub `tkinter`; w etapie 1 zwykła konsola | Wybór trybu, podgląd telemetrii, postęp nauki |
| Zapis | SQLite | Okrążenia, najlepsze czasy, postęp w zdejmowaniu asyst |
| Testy | `pytest` + nagrane pakiety UDP jako dane testowe | Silnik testowany bez włączonej gry |
| Pakowanie | `PyInstaller` | Jeden plik `.exe` do udostępnienia |

Przepływ danych: gra → UDP → parser → model danych → kolejka zdarzeń → silnik (trener lub inżynier) → komunikat → odtwarzacz głosu. Interfejs tylko czyta stan, nigdy nie liczy.

Zasada kluczowa: silnik dostaje strumień pakietów i zwraca listę komunikatów. Dzięki temu można mu podać nagranie z pliku zamiast żywej gry, a później podpiąć inny interfejs (telefon, nakładka).

## Struktura projektu

Repozytorium `boxbox-academy`, jeden pakiet `boxbox/` podzielony według warstw z tabeli wyżej. Claude Code dostaje `CLAUDE.md` w katalogu głównym i ten plan jako `PLAN.md`.

```markdown
boxbox-academy/
├── CLAUDE.md              # zasady projektu dla Claude Code
├── PLAN.md                # ten dokument
├── pyproject.toml
├── boxbox/
│   ├── telemetry/         # odbiór UDP, parser pakietów, modele danych
│   ├── tracks/            # JSON z zakrętami dla każdego toru
│   ├── coach/             # tryb nauki: analiza zakrętów, gaz/hamulec, ERS, postęp
│   ├── engineer/          # tryb wyścigowy: opony, pit, flagi, rywale
│   ├── voice/             # klipy, składanie zdań, efekt radia, rozpoznawanie komend
│   ├── storage/           # SQLite: okrążenia, czasy, postęp
│   ├── ui/                # konsola (etap 1), potem okno
│   └── app.py             # spina wszystko, wybór trybu
├── assets/
│   └── voice/             # wygenerowane klipy WAV
├── recordings/            # nagrane sesje UDP do testów i odtwarzania
└── tests/
```

Treść `CLAUDE.md` (do wklejenia):

```markdown
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
```

## Etapy realizacji

Siedem etapów, każdy z kryterium ukończenia, które da się sprawdzić bez dyskusji. Jeden etap = jedna lub kilka sesji Claude Code. Kolejny etap zaczyna się dopiero po spełnieniu kryterium poprzedniego.

**Etap 0 – Szkielet (1 sesja)** ✔ zakończony

- [x] Repozytorium Git, `pyproject.toml`, struktura katalogów z sekcji wyżej, `CLAUDE.md`, pusty `pytest` przechodzi.
- [x] Kryterium: `pytest` zielony, `python -m boxbox.app` uruchamia się i wypisuje "brak danych".

**Etap 1 – Telemetria (2–3 sesje)** ✔ zakończony (26.10.2026)

- [x] Odbiór UDP na porcie 20777, parser nagłówka pakietu i pakietów: Session, Lap Data, Car Telemetry, Car Status, Event, Car Damage. (Układy pól sprawdzone ze specyfikacją EA w `docs/`; do potwierdzenia pierwszym nagraniem.)
- [x] Narzędzie `record` (`python -m boxbox.telemetry.record --name <tor>`) zapisujące surowe pakiety do pliku i `replay` (`python -m boxbox.app --replay <plik> [--speed N]`) odtwarzający je z zachowaniem czasu.
- [x] Konsola pokazująca na żywo: prędkość, bieg, gaz %, hamulec %, baterię %, dystans okrążenia, aktualne asysty.
- [x] Kryterium: 3 nagrania (trening na 3 torach) w `recordings/`, test parsera na każdym z nich przechodzi. (Bahrajn TT 156 574 pakiety, Monza trening z AI 287 129, Suzuka TT bez TC 125 536; 0 błędów parsera; nagrania jako `.bin.xz`, test: `tests/test_recordings.py`.)

**Etap 2 – Zakręty i okrążenie referencyjne (2 sesje)** ✔ zakończony (26.10.2026)

- [x] Format JSON toru: lista zakrętów z numerem, dystansem wejścia i wyjścia. Pliki dla 3 torów z nagrań. (`boxbox/tracks/data/`: `3.json` Bahrajn 8 stref, `11.json` Monza 6, `13.json` Suzuka 5; strefy hamowania wykryte z nagrań, nazwy wg numerów zakrętów toru; `python -m boxbox.tracks.detect <nagranie> [--car rival]`.)
- [x] Dzielenie okrążenia na zakręty; dla każdego: minimalna prędkość, bieg w apexie, punkt hamowania, punkt pełnego gazu. (`boxbox/coach/laps.py`, `corners.py`, tabela: `python -m boxbox.coach.analyze <nagranie>`; sprawdzone na danych syntetycznych.)
- [x] Zapis okrążeń do SQLite; najlepsze ważne okrążenie gracza staje się referencją. (`boxbox/storage/db.py`, domyślnie `data/boxbox.sqlite`.)
- [x] Kryterium: po odtworzeniu nagrania aplikacja wypisuje tabelę zakrętów z różnicą do referencji. (`python -m boxbox.app --replay recordings/bahrajn-tt_...bin.xz [--reference rival]`: różnica do własnego najlepszego albo do ducha rywala.)

**Etap 3 – Trener gaz/hamulec (2–3 sesje)** ✔ zakończony (26.10.2026)

- [x] Reguły: hamowanie za późno/za wcześnie, brak stopniowego puszczania hamulca, gaz za wcześnie (poślizg kół na wyjściu), za niski/za wysoki bieg w apexie. (`boxbox/coach/rules.py`; dodatkowo: utrata przyczepności/obrót, pełny gaz za późno. Poślizg kół liczony pośrednio: brak pakietu Motion Ex w nagraniach, więc po prędkości wyjścia i v_min.)
- [x] Każda reguła zwraca komunikat: zakręt, problem, wskazówka, waga. (`Message`; waga = strata czasu w zakręcie względem referencji.)
- [x] Po okrążeniu wybór 2–3 komunikatów o największej wadze. (`pick_top`: jeden na zakręt, próg 0,5 s; w aplikacji linia „Trener:” pod tabelą.)
- [x] Kryterium: test na nagraniu ze znanym błędem wykrywa go; na czystym okrążeniu milczy. (`tests/test_rules.py` na Monzie, Suzuce i Bahrajnie; progi dobrane do tych nagrań, do weryfikacji na żywo w etapie 4.)

**Etap 4 – Głos (2 sesje)**

- [x] Lista wszystkich zdań jako szablony: fragment stały + zakręt + wartość. Wygenerowanie klipów przez TTS (jeden głos), efekt radia nałożony skryptem. (Katalog: `boxbox/voice/phrases.py`, 96 fraz, `assets/voice/phrases.csv`; ElevenLabs Creator, głos „Piotr – Neutral and Mature Bard”, `tools/generate_voice_elevenlabs.py`; klipy w `assets/voice/raw`, z efektem radia w `assets/voice`.)
- [x] Składanie zdania z klipów i odtwarzanie bez blokowania odbioru telemetrii (osobny wątek). (`boxbox/voice/player.py`: biblioteka klipów w pamięci, kolejka maks. 3, wątek; Windows `winsound`, Linux/macOS `aplay`/`afplay`. Efekt radia: `boxbox/voice/radio.py`, czysty Python.)
- [x] Komunikat po zakręcie i podsumowanie po okrążeniu mówione głosem. (`boxbox/coach/live.py`; w aplikacji `--voice`, `--volume`, `--corner-messages`; `trener.bat`. Po 1. teście na żywo: głos działa, dodane komunikaty startowe, okrążenie wyjazdowe, „najwięcej do zyskania” na czystym okrążeniu, progi 0,3 s, głośniejsze klipy.)
- [ ] Kryterium: przejazd na żywo z włączoną grą, komunikat słychać do 2 s po wyjściu z zakrętu.

**Etap 5 – Bateria, asysty, postęp (2 sesje)**

- [x] Analiza ERS: deploy na odcinek toru, zysk czasu, bateria na ostatnim okrążeniu. (`coach/ers.py`, rada po okrążeniu bez asysty ERS)
- [x] Ścieżka zdejmowania asyst z celami (np. 3 czyste okrążenia z rzędu) i komunikat, kiedy przejść dalej. Trener zmienia nacisk reguł po zdjęciu asysty. (`coach/progress.py`, `rules.emphasize`, tabela `progress`)
- [x] Ekran postępu: tor, zakręty opanowane, aktualny krok asyst. (`python -m boxbox.app --progress`)
- [ ] Kryterium: po nagraniu sesji aplikacja pokazuje postęp i proponuje kolejny krok. (do potwierdzenia na żywo – protokół testu partii 1)

**Etap 6 – Tryb wyścigowy i wydanie (3 sesje)**

- [ ] Reguły inżyniera: temperatura i zużycie opon, okno pit-stopu, flagi, przewaga/strata do rywali, uszkodzenia, deszcz. (teksty klipów gotowe: `engineer/phrases.py`, generowane razem z resztą)
- [ ] Komendy głosowe: 5–8 pytań z lokalnym rozpoznawaniem mowy.
- [ ] Okno aplikacji z wyborem trybu, instrukcją włączenia telemetrii w grze i sprawdzeniem połączenia.
- [ ] `PyInstaller` → jeden `.exe`, test na czystym Windowsie.
- [ ] Kryterium: pełny wyścig na żywo bez awarii, `.exe` uruchamia się u drugiej osoby.

## Droga do bety: platforma dla początkujących w simracingu (dodane 27.10.2026)

Cel: wersja beta, którą każdy uruchomi dwuklikiem, obsługująca F1 25 i 2026 Season Pack, użyteczna
na poziomie Trophy AI albo lepsza. Różnica względem konkurencji: trener mówi i tłumaczy, prowadzi
początkującego krok po kroku (asysty, start, opony, bateria), a postęp jest widoczny na każdym kroku,
żeby gracz chciał wracać. Etapy 0–5 (silnik, głos, postęp) są fundamentem; poniżej plan bety.

**Decyzje do podjęcia przed etapem 6**

- [x] GUI: `PySide6` (Qt), decyzja 27.10: rozmiar pliku bez znaczenia, zero wyskakujących okien, PDF przez okno drukowania Windows. Propozycja była: natywne okno, wykresy (QtCharts), eksport PDF z okna, dymki podpowiedzi, obraz w karcie kierowcy, działa w `.exe`; licencja LGPL dopuszcza użytek komercyjny. Alternatywa: interfejs w przeglądarce (HTML + wykresy JS) w oknie `pywebview`. Obie wymagają nowej zależności, więc wybór należy do właściciela projektu.
- [ ] Język: polski na start, teksty w jednym pliku, żeby angielski dało się dodać bez zmian w kodzie.
- [ ] Identyfikator gracza: lokalny UUID + nick w profilu; ranking (chmura) dopiero po becie, z wyraźną zgodą gracza.

**Etap 6 – Aplikacja okienkowa i profil (3–4 sesje)**

- [x] Okno główne w stylu wyścigowym (ciemne, czerwony akcent jak logo): panel startowy z wyborem trybu, stanem połączenia z grą i jednym przyciskiem „Jedź”. Trener i nakładka startują z okna, bez terminala. (`boxbox/gui`, `akademia.bat`)
- [x] Kreator pierwszego uruchomienia: sprawdza ustawienia telemetrii w grze (nasłuch pakietów, port, format), podpowiada, co włączyć; test głośników; wybór asyst na start.
- [x] Karta kierowcy: nick, zdjęcie, ID gracza, liczba sesji i okrążeń, aktualny krok asyst na każdym torze, najlepsze czasy. (ulubiony tor: później)
- [x] Samouczek: dymki z opisem każdego elementu okna przy pierwszym użyciu, do wyłączenia; teksty w jednym pliku (`gui/texts.py`), żeby później podłożyć lektora.
- [ ] Jeden plik `.exe` przez PyInstaller (z klipami głosu i plikami torów), uruchomienie dwuklikiem, test na czystym Windowsie. (`zbuduj_akademia.bat` gotowy; klipy obok .exe; test na Windows do zrobienia)
- [ ] Kryterium: osoba, która nigdy nie widziała projektu, uruchamia `.exe`, przechodzi kreator i jedzie sesję z trenerem bez pomocy.

**Etap 7 – Analiza telemetrii i wykresy (3 sesje)**

- [ ] Wykresy okrążenia względem dystansu: prędkość, gaz, hamulec, bieg, kierownica, ERS, DRS; nałożenie na okrążenie referencyjne (własne najlepsze, duch Time Trial, AI) i delta czasu w każdym punkcie toru.
- [ ] Mapa toru z realnego kształtu (recorder) z punktami hamowania, apeksami, strefami DRS i miejscem każdej uwagi trenera; mapa także na nakładce.
- [ ] Tabela przejazdów dla każdego toru: sesje, okrążenia, czasy, sektory, asysty, ważność, uwagi trenera; filtry i sortowanie; porównanie dwóch okrążeń obok siebie.
- [ ] Eksport: telemetria okrążenia do CSV, raport sesji do PDF z wykresami, mapą i uwagami trenera (jeden przycisk).
- [ ] Kryterium: po sesji gracz widzi, gdzie traci czas i dlaczego, bez słuchania komunikatów.

**Etap 8 – Trener 2.0: optymalne punkty i wyjaśnianie (3–4 sesje)**

- [ ] Optymalny punkt hamowania w każdym zakręcie: z najlepszych własnych okrążeń, ducha i AI; trener mówi „hamuj przy tablicy 100 m”, a na mapie i nakładce widać znacznik; „próbuj 5 m później” jako cel na następne okrążenie.
- [ ] Optymalne dodanie gazu i trail-braking: punkt pełnego gazu, krzywa puszczania hamulca, bieg w apeksie; porównanie z referencją jako cel na zakręt.
- [ ] DRS: wykrywanie stref z pakietu Session, czas reakcji na włączenie, uwaga „DRS włączony o 0,4 s za późno”, ćwiczenie na prostych.
- [ ] Bateria: plan deployu na okrążenie (gdzie zyskuje najwięcej), tryb przeglądu/hotlap, ostrzeżenie o pustej baterii przed prostą, ocena po okrążeniu z liczbą.
- [ ] Tryb „wytłumacz mi”: przy pierwszym wystąpieniu każdej uwagi trener mówi dłuższą wersję (co to jest trail-braking, czemu TC pomaga, jak czytać deltę); później krótko. Słownik pojęć w oknie.
- [ ] Lekcje: zestaw krótkich ćwiczeń (np. „hamowanie w T1: 5 okrążeń, cel 10 m później co okrążenie”), postęp lekcji widoczny w karcie kierowcy.
- [ ] Kryterium: na nagraniu początkującego trener wskazuje punkt hamowania i gazu w każdym zakręcie z celem na kolejne okrążenie; na nagraniu szybkiego gracza milczy.

**Etap 9 – Opony, start i walka na torze (3 sesje)**

- [ ] Opony: temperatury i zużycie per okrążenie, okno temperatur, uwagi „przegrzewasz tył na wyjściach”, „ziarnienie”, prognoza żywotności zestawu na dystans wyścigu; lekcja oszczędzania opon.
- [ ] Start: czas reakcji od zgaszenia świateł (zdarzenie LGOT), uślizg kół, pozycje zyskane/stracone do T1; lekcja startu: sprzęgło/gaz, trzymanie linii, zostawianie miejsca, pierwsze okrążenie bez kontaktu.
- [ ] Walka: kolizje z pakietu Event (kto, gdzie, siła), ocena bezpieczeństwa jazdy (safety rating), zasady obrony i ataku tłumaczone przez trenera po sytuacji, nie w jej trakcie.
- [ ] Inżynier na radiu (tryb wyścigowy, teksty klipów gotowe): opony, okno pit-stopu, flagi, SC/VSC, odstępy, uszkodzenia, deszcz, paliwo.
- [ ] Kryterium: pełny wyścig z AI bez awarii, po wyścigu raport ze startu, kontaktów i zarządzania oponami.

**Etap 10 – Postęp i motywacja (2 sesje)**

- [ ] Panel postępu na każdy tor: krok asyst, seria, trend czasów (wykres), zakręty opanowane, spójność (rozrzut czasów), odsetek czystych okrążeń.
- [ ] Odznaki i cele dnia: pierwsze czyste okrążenie, pierwsze okrążenie bez TC, 10 sesji, tor opanowany; seria dni z treningiem.
- [ ] Historia: każda sesja z podsumowaniem i raportem PDF do pobrania; porównanie „ty miesiąc temu vs dziś”.
- [ ] Kryterium: po każdej sesji gracz widzi co najmniej jedną rzecz, która się poprawiła.

**Etap 11 – Wydanie beta (2 sesje)**

- [ ] Test na 3–5 początkujących z formularzem z `docs/PLAN_TESTOW.md`; lista błędów i poprawki.
- [ ] Zgłaszanie błędów z aplikacji: przycisk „wyślij raport” pakuje dziennik, bazę i ostatnie nagranie (recorder).
- [ ] Sprawdzenie aktualizacji z GitHub Releases, podpis `.exe` albo instrukcja dla antywirusa.
- [ ] Oba formaty telemetrii (2025 i 2026) przetestowane na żywo na 3 torach; pozostałe tory: pliki torów z recordera i automatycznego wykrywania zakrętów.
- [ ] Kryterium: beta na GitHub Releases, instalacja i pierwsza sesja u obcej osoby bez pomocy.

**Po becie** (nie w zakresie bety): ranking i konta w chmurze (nick + ID z karty kierowcy), lektor w samouczku, swobodna rozmowa z mechanikiem (model językowy), wersja mobilna jako podgląd, więcej gier.

**Pomysły od Claude** (dopisane do etapów wyżej, tu dla przejrzystości): kreator sprawdzający telemetrię gry zamiast instrukcji; delta czasu na żywo na nakładce; mapa toru z realnego kształtu z punktami hamowania; cel „5 m później” na następne okrążenie zamiast ogólnych uwag; tryb „wytłumacz mi” z dłuższą wersją uwagi przy pierwszym wystąpieniu; lekcje z jednym celem; ocena bezpieczeństwa jazdy ze zdarzeń kolizji; czas reakcji na start ze zdarzenia LGOT; spójność i odsetek czystych okrążeń jako miary postępu; odznaki; raport sesji PDF jednym przyciskiem; przycisk „wyślij raport błędu” oparty na recorderze; teksty w jednym pliku pod angielski i lektora.

## Zasady pracy z Claude Code

Jedna sesja = jedno zadanie z listy etapu, zaczynane od testu, kończone commitem. Dzięki temu Claude Code nie gubi kontekstu, a Ty uczysz się po kawałku.

1. Otwórz sesję w katalogu projektu i zacznij od: "Przeczytaj CLAUDE.md i PLAN.md. Jesteśmy w etapie N. Zrób zadanie: \<wklej punkt z listy>".
2. Poproś najpierw o plan zmian i listę plików, dopiero potem o kod. Przy większym zadaniu: "najpierw napisz test, potem implementację".
3. Po każdym zadaniu: `pytest`, krótkie uruchomienie na nagraniu z `recordings/`, commit z opisem `etap-N: <co zrobiono>`.
4. Zaznacz punkt w PLAN.md jako zrobiony. Etap zamykasz dopiero, gdy jego kryterium ukończenia jest spełnione.
5. Nowy pomysł w trakcie etapu trafia do sekcji "Pytania otwarte", nie do kodu.
6. Gdy coś nie działa z żywą grą, najpierw nagraj sesję i odtwarzaj ją z pliku; debugowanie na żywo jest wolne i frustrujące.
7. Prośby o wyjaśnienie kodu są częścią pracy: "wytłumacz, co robi ten parser i dlaczego używa `struct.unpack`" – projekt ma uczyć, nie tylko działać.

## Ryzyka i pytania otwarte

| Ryzyko | Skutek | Co zrobić |
| --- | --- | --- |
| Format pakietów UDP F1 25 różni się od F1 24 | Parser czyta śmieci | Zrobione: specyfikacja w `docs/`, parsery sprawdzone z nią. Obsługiwane oba formaty: 2025 (gra) i 2026 (2026 Season Pack, 24 auta, pakiet Car Telemetry 2); wybór po polu `packetFormat` w nagłówku. Potwierdzone na nagraniach: 2025 (Bahrajn, Monza, Suzuka) i 2026 (`recordings/pakiet2026-monza_...`), 0 błędów parsera |
| Ręczne mapowanie zakrętów dla 24 torów | Dużo żmudnej pracy | MVP na 3 torach; zrobione: `boxbox/tracks/detect.py` wyznacza zakręty z profilu prędkości nagrania (do sprawdzenia na prawdziwych danych, progi mogą wymagać strojenia) |
| Opóźnienie głosu | Komunikat przychodzi za późno i myli | Odtwarzanie w osobnym wątku, klipy w pamięci, limit 1 komunikat na zakręt |
| Za dużo komunikatów | Gracz wyłącza aplikację | Progi wag, cisza na czystym okrążeniu, maks. 3 uwagi po okrążeniu |
| Jeden głos TTS brzmi sztucznie | Spada klimat | Decyzja: ElevenLabs (plan free: użytek niekomercyjny, wymagane podanie źródła), zdania składane tak, by sklejać tylko liczby; efekt radia; docelowo nagranie prawdziwego lektora |
| Udostępnianie `.exe` | Antywirusy blokują nieznane pliki | Podpis kodu albo instrukcja dla użytkownika; wersja z GitHub Releases |

Pytania otwarte:

- [ ] Skąd okrążenie referencyjne dla kogoś, kto dopiero zaczyna: własne najlepsze, czy dołączone wzorcowe okrążenia z gry? Ustalone na nagraniu Bahrajn TT: duch rywala jest w pakietach (indeks `time_trial_rival_car_idx`, u nas 5) z prędkością, gazem, hamulcem i czasem okrążenia; część próbek ma śmieciową prędkość >340 km/h, do odfiltrowania. Kandydaci: (a) auto AI z tej samej sesji na wysokim poziomie trudności (gra wysyła telemetrię wszystkich 22 aut), (b) duch rywala w Time Trial, jeśli jego telemetria leci po UDP (Lap Data ma `time_trial_rival_car_idx`), (c) nagranie od szybkiego gracza przez `record`.
- [ ] Czy w trybie nauki mechanik ma w ogóle mówić podczas okrążenia, czy tylko po nim?
- [ ] Jaki język komunikatów domyślnie: polski, angielski, oba?
- [ ] Czy rozwijać projekt publicznie na GitHubie od początku (dla CV i kanału), czy po MVP?
