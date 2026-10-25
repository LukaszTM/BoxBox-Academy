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

**Poza zakresem MVP** (do dopisania później): swobodna rozmowa z mechanikiem przez model językowy i klucz API, wersja mobilna, nakładka na ekranie gry, konta użytkowników i chmura.

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

**Etap 0 – Szkielet (1 sesja)**

- [x] Repozytorium Git, `pyproject.toml`, struktura katalogów z sekcji wyżej, `CLAUDE.md`, pusty `pytest` przechodzi.
- [x] Kryterium: `pytest` zielony, `python -m boxbox.app` uruchamia się i wypisuje "brak danych".

**Etap 1 – Telemetria (2–3 sesje)**

- [ ] Odbiór UDP na porcie 20777, parser nagłówka pakietu i pakietów: Session, Lap Data, Car Telemetry, Car Status, Event, Car Damage.
- [ ] Narzędzie `record` zapisujące surowe pakiety do pliku i `replay` odtwarzający je z zachowaniem czasu.
- [ ] Konsola pokazująca na żywo: prędkość, bieg, gaz %, hamulec %, baterię %, dystans okrążenia, aktualne asysty.
- [ ] Kryterium: 3 nagrania (trening na 3 torach) w `recordings/`, test parsera na każdym z nich przechodzi.

**Etap 2 – Zakręty i okrążenie referencyjne (2 sesje)**

- [ ] Format JSON toru: lista zakrętów z numerem, dystansem wejścia i wyjścia. Pliki dla 3 torów z nagrań.
- [ ] Dzielenie okrążenia na zakręty; dla każdego: minimalna prędkość, bieg w apexie, punkt hamowania, punkt pełnego gazu.
- [ ] Zapis okrążeń do SQLite; najlepsze ważne okrążenie gracza staje się referencją.
- [ ] Kryterium: po odtworzeniu nagrania aplikacja wypisuje tabelę zakrętów z różnicą do referencji.

**Etap 3 – Trener gaz/hamulec (2–3 sesje)**

- [ ] Reguły: hamowanie za późno/za wcześnie, brak stopniowego puszczania hamulca, gaz za wcześnie (poślizg kół na wyjściu), za niski/za wysoki bieg w apexie.
- [ ] Każda reguła zwraca komunikat: zakręt, problem, wskazówka, waga.
- [ ] Po okrążeniu wybór 2–3 komunikatów o największej wadze.
- [ ] Kryterium: test na nagraniu ze znanym błędem wykrywa go; na czystym okrążeniu milczy.

**Etap 4 – Głos (2 sesje)**

- [ ] Lista wszystkich zdań jako szablony: fragment stały + zakręt + wartość. Wygenerowanie klipów przez TTS (jeden głos), efekt radia nałożony skryptem.
- [ ] Składanie zdania z klipów i odtwarzanie bez blokowania odbioru telemetrii (osobny wątek).
- [ ] Komunikat po zakręcie i podsumowanie po okrążeniu mówione głosem.
- [ ] Kryterium: przejazd na żywo z włączoną grą, komunikat słychać do 2 s po wyjściu z zakrętu.

**Etap 5 – Bateria, asysty, postęp (2 sesje)**

- [ ] Analiza ERS: deploy na odcinek toru, zysk czasu, bateria na ostatnim okrążeniu.
- [ ] Ścieżka zdejmowania asyst z celami (np. 3 czyste okrążenia z rzędu) i komunikat, kiedy przejść dalej. Trener zmienia nacisk reguł po zdjęciu asysty.
- [ ] Ekran postępu: tor, zakręty opanowane, aktualny krok asyst.
- [ ] Kryterium: po nagraniu sesji aplikacja pokazuje postęp i proponuje kolejny krok.

**Etap 6 – Tryb wyścigowy i wydanie (3 sesje)**

- [ ] Reguły inżyniera: temperatura i zużycie opon, okno pit-stopu, flagi, przewaga/strata do rywali, uszkodzenia, deszcz.
- [ ] Komendy głosowe: 5–8 pytań z lokalnym rozpoznawaniem mowy.
- [ ] Okno aplikacji z wyborem trybu, instrukcją włączenia telemetrii w grze i sprawdzeniem połączenia.
- [ ] `PyInstaller` → jeden `.exe`, test na czystym Windowsie.
- [ ] Kryterium: pełny wyścig na żywo bez awarii, `.exe` uruchamia się u drugiej osoby.

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
| Format pakietów UDP F1 25 różni się od F1 24 | Parser czyta śmieci | Przed etapem 1 pobrać oficjalną specyfikację telemetrii F1 25 z forum EA i trzymać ją w `docs/` |
| Ręczne mapowanie zakrętów dla 24 torów | Dużo żmudnej pracy | MVP na 3 torach; narzędzie, które wyznacza zakręty automatycznie z profilu prędkości na nagraniu |
| Opóźnienie głosu | Komunikat przychodzi za późno i myli | Odtwarzanie w osobnym wątku, klipy w pamięci, limit 1 komunikat na zakręt |
| Za dużo komunikatów | Gracz wyłącza aplikację | Progi wag, cisza na czystym okrążeniu, maks. 3 uwagi po okrążeniu |
| Jeden głos TTS brzmi sztucznie | Spada klimat | Efekt radia maskuje dużo; docelowo nagranie prawdziwego lektora |
| Udostępnianie `.exe` | Antywirusy blokują nieznane pliki | Podpis kodu albo instrukcja dla użytkownika; wersja z GitHub Releases |

Pytania otwarte:

- [ ] Skąd okrążenie referencyjne dla kogoś, kto dopiero zaczyna: własne najlepsze, czy dołączone wzorcowe okrążenia z gry?
- [ ] Czy w trybie nauki mechanik ma w ogóle mówić podczas okrążenia, czy tylko po nim?
- [ ] Jaki język komunikatów domyślnie: polski, angielski, oba?
- [ ] Czy rozwijać projekt publicznie na GitHubie od początku (dla CV i kanału), czy po MVP?
