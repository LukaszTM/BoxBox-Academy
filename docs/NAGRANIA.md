# BoxBox Academy – instrukcja nagrywania telemetrii

Potrzebne są trzy nagrania z F1 25 na trzech torach. Posłużą do testów parsera (etap 1),
do wyznaczenia zakrętów i okrążenia referencyjnego (etap 2) oraz do testów reguł trenera
(etap 3). Nie musisz jeździć szybko. Twoje błędy są właśnie tym, czego trener ma się nauczyć wykrywać.

Każda sesja to około 15 minut: 6 okrążeń plus ustawienia.

## 1. Przygotowanie komputera

1. Zainstaluj Python 3.12 lub nowszy z https://www.python.org/downloads/ (zaznacz „Add python.exe to PATH”).
2. Rozpakuj `boxbox-recorder.zip` do dowolnego folderu, np. `C:\boxbox-recorder`.
3. Otwórz ten folder w Eksploratorze, kliknij w pasek adresu, wpisz `cmd` i naciśnij Enter. Otworzy się terminal w tym folderze.
4. Sprawdź, że Python działa: wpisz `py -3 --version`. Powinno wypisać wersję 3.12 lub nowszą.

Paczka nie wymaga żadnych dodatkowych bibliotek.

## 2. Ustawienia telemetrii w grze

W F1 25: **Ustawienia → Ustawienia telemetrii** (Settings → Telemetry Settings).

| Ustawienie | Wartość |
| --- | --- |
| Telemetria UDP (UDP Telemetry) | Wł. |
| Tryb rozgłaszania UDP (UDP Broadcast Mode) | Wył. |
| Adres IP UDP | 127.0.0.1 (gra i recorder na tym samym PC) |
| Port UDP | 20777 |
| Częstotliwość wysyłania (UDP Send Rate) | 60 Hz |
| Format UDP | 2025 (po zakupie 2026 Season Pack: 2026) |
| Twoja telemetria (Your Telemetry) | Publiczna |

Jeśli po pierwszym nagraniu podsumowanie pokaże „nieobsługiwany format”, wróć tutaj i sprawdź Format UDP.

## 3. Ustawienia sesji, wspólne dla wszystkich nagrań

- **Pogoda:** słonecznie, tor suchy. W Time Trial jest tak zawsze. W treningu ustaw pogodę na „Bezchmurnie” i wyłącz pogodę dynamiczną.
- **Pora dnia:** dzień.
- **Auto:** dowolny zespół F1 (nie F2). W Time Trial zostaw „Równe osiągi” włączone.
- **Flashback:** nie używaj podczas nagrania. Jeśli coś pójdzie źle, jedź dalej i zanotuj numer okrążenia.
- **Uszkodzenia:** standardowe. **Kolizje:** włączone.
- **Asysty:** w sesjach 1 i 2 takie, na jakich zwykle jeździsz (np. automatyczna skrzynia, TC pełna, ABS wł.). Sesja 3 ma inne asysty, patrz niżej. Linia jazdy może zostać włączona.

## 4. Schemat jazdy, taki sam na każdym torze

| Okrążenie | Co robić |
| --- | --- |
| 1 | Wyjazdowe z pit lane. Spokojnie, bez pośpiechu. |
| 2–3 | Dwa czyste okrążenia: hamuj w rozsądnych miejscach, nie wyjeżdżaj poza tor, nie ścinaj. |
| 4–5 | Dwa okrążenia z celowymi błędami w trzech wskazanych zakrętach (tabela niżej). Resztę toru jedź normalnie. |
| 6 | Zjazd do pit lane, zakończenie nagrania. |

Celowe błędy, po jednym na zakręt:

- **Za późne hamowanie:** zacznij hamować wyraźnie później niż na czystym okrążeniu. Wyjazd szeroko jest w porządku, to ma być widoczne.
- **Gaz za wcześnie:** w apeksie wciśnij gaz do oporu od razu. Przy TC pełnej auto się nie obróci, ale telemetria to pokaże.
- **Hamulec puszczony naraz:** zahamuj mocno i w połowie hamowania puść pedał całkiem, zamiast stopniowo.

Jeśli auto się obróci albo wylądujesz na żwirze, nie cofaj czasu. Zjedź na tor i jedź dalej. Zanotuj to w pliku z notatkami.

## 5. Trzy sesje

### Sesja 1: Bahrajn, Time Trial, z duchem rywala

- Tryb: **Time Trial**, tor **Bahrajn (Sakhir)**.
- Przed startem wybierz **ducha rywala** z tablicy wyników: kogoś z pierwszych 100 miejsc. Jego przejazd może posłużyć jako okrążenie wzorcowe, jeśli gra wysyła jego telemetrię.
- Nazwa nagrania: `bahrajn-tt`.
- Błędy na okrążeniach 4 i 5: zakręt 1 (za późne hamowanie), zakręt 4 (gaz za wcześnie), zakręt 10 (hamulec puszczony naraz).

### Sesja 2: Monza, trening z AI

- Tryb: **Grand Prix → Monza → Trening 1** (albo Trening skrócony). Długość sesji: krótka.
- Poziom trudności AI: **100** lub wyżej. Auta AI mają jeździć po torze, bo ich przejazdy to drugi kandydat na okrążenie wzorcowe.
- Nazwa nagrania: `monza-trening`.
- Błędy na okrążeniach 4 i 5: zakręt 1 (pierwsza szykana, za późne hamowanie), zakręt 7 (Lesmo 2, gaz za wcześnie), zakręt 11 (Parabolica, hamulec puszczony naraz).
- Jeśli na torze jest ruch, nie przejmuj się przepuszczaniem. Liczy się Twoje okrążenie.

### Sesja 3: Suzuka, Time Trial, bez kontroli trakcji

- Tryb: **Time Trial**, tor **Suzuka**.
- Asysty: **TC wyłączona**, reszta jak zwykle (skrzynia i ABS bez zmian). To nagranie pokaże, jak wygląda jazda po zdjęciu asysty, i przyda się w etapie 5.
- Nazwa nagrania: `suzuka-tt-bez-tc`.
- Błędy na okrążeniach 4 i 5: zakręt 1 (za późne hamowanie), zakręt 14 (Spoon, gaz za wcześnie – tu bez TC auto może zatańczyć, to w porządku), zakręt 11 (spinka, hamulec puszczony naraz).

Po zakupie 2026 Season Pack: jedna dodatkowa, dowolna sesja z Formatem UDP 2026, nazwa `pakiet2026-<tor>`.

## 6. Nakładka na grę (zalecane)

Zamiast `nagraj.bat` możesz uruchomić nakładkę, która jednocześnie nagrywa i pokazuje nad grą:
numer okrążenia i cel na nie, zbliżający się zakręt (numer jak w grze, odległość) oraz zadanie
do zrobienia w tym zakręcie na okrążeniach z błędami.

1. W grze: **Ustawienia graficzne → Tryb okna: Bez ramki** (w pełnym ekranie nakładka nie będzie widoczna).
2. W terminalu: `nakladka.bat <nazwa-nagrania> <plan>`, np. `nakladka.bat bahrajn-tt bahrajn-tt`.
   Plany: `bahrajn-tt`, `monza-trening`, `suzuka-tt-bez-tc`, `pakiet2026`.
3. Okno pojawi się w lewym górnym rogu; przeciągnij je tam, gdzie nie zasłania toru. Nie klikaj w nie podczas jazdy, bo zabiera grze klawiaturę.
4. Po sesji naciśnij **Esc** na nakładce (albo zamknij okno). Nagranie zostaje zapisane jak przy `nagraj.bat`.

Pozycje zakrętów dla Bahrajnu są z nagrania. Dla Monzy i Suzuki są orientacyjne, więc **pierwsze (wyjazdowe)
okrążenie służy do kalibracji**: nakładka wykrywa, gdzie hamujesz, i od drugiego okrążenia pokazuje
zakręty w prawdziwych miejscach. Skalibrowany przewodnik zapisuje się obok nagrania jako `.guide.json`;
prześlij go razem z nagraniem.

## 7. Jak nagrywać, krok po kroku

1. Uruchom grę i wejdź do garażu wybranej sesji, ale jeszcze nie wyjeżdżaj.
2. W terminalu wpisz `nagraj.bat bahrajn-tt` (nazwa z sekcji 5). Zobaczysz „Nasłuchuję na porcie 20777”.
3. Wyjedź na tor. W terminalu pojawi się „Odbieram dane z gry, nagrywam...”. Jeśli nie pojawi się w ciągu kilku sekund, patrz sekcja 9.
4. Przejedź 6 okrążeń według schematu.
5. Po zjeździe do pit lane przejdź do terminala i naciśnij **Ctrl+C**. Zobaczysz „Zapisano N pakietów”.
6. Od razu uzupełnij notatki: w folderze `recordings` jest plik `.txt` o tej samej nazwie co nagranie. Wpisz tor, asysty i listę błędów: numer okrążenia, numer zakrętu, rodzaj błędu. Wpisz też, jeśli coś poszło nie tak (obrót, żwir, kolizja).
7. Sprawdź nagranie: `sprawdz.bat recordings\bahrajn-tt_<data>.bin`. Podsumowanie powinno pokazać pakiety CAR_TELEMETRY, LAP_DATA, SESSION, CAR_STATUS bez błędów parsera i format 2025.

Przykład notatek:

```
Tor: Bahrajn, Time Trial, duch rywala: tak
Asysty (skrzynia / TC / ABS): automat / pełna / wł.
Okrążenia i błędy:
4, Z1, za późne hamowanie (wyjazd szeroko)
4, Z4, gaz za wcześnie
4, Z10, hamulec puszczony naraz
5, Z1, za późne hamowanie
5, Z4, gaz za wcześnie, auto lekko poślizg
5, Z10, hamulec puszczony naraz
Uwagi: na okrążeniu 3 lekko ściąłem Z2, okrążenie mogło być nieważne
```

## 8. Co zrobić z plikami

Z folderu `recordings` weź pliki `.bin`, `.txt` i (z nakładki) `.guide.json`. Plik `.bin` ma ok. 170 MB;
spakuj go do ZIP lub RAR (zostaje ok. 12 MB) i prześlij w sesji Claude Code jako załącznik razem z `.txt`
i `.guide.json`. Do repozytorium trafia skompresowana wersja `.bin.xz`, to już robi Claude.

## 9. Gdy coś nie działa

| Objaw | Co sprawdzić |
| --- | --- |
| Nakładki nie widać nad grą | Gra w pełnym ekranie. Ustawienia graficzne → Tryb okna: Bez ramki. |
| Nakładka pokazuje „brak przewodnika toru” | Dla tego toru nie ma pliku z zakrętami; nagranie i tak jest poprawne. |
| „Nie odebrano żadnego pakietu” | Telemetria UDP włączona? IP 127.0.0.1 i port 20777? Czy inny program (np. SimHub) nie zajmuje portu 20777? Zamknij go na czas nagrania. |
| Zapora Windows pyta o Pythona | Zezwól na sieci prywatne. |
| „Nieobsługiwany format pakietu” w podsumowaniu | Format UDP w grze ustaw na 2025 (lub 2026 z Season Pack). |
| Błędy parsera przy jakimś typie pakietu | Nic nie rób, prześlij nagranie. To informacja dla mnie, że układ pakietu wymaga poprawki. |
| `py` nie jest rozpoznawane | Python nie jest w PATH. Zainstaluj ponownie z zaznaczonym „Add python.exe to PATH” albo użyj pełnej ścieżki do `python.exe`. |
