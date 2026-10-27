# BoxBox Academy – specyfikacja funkcji i rozpiska do makiety

Wersja 1.0, 27.10.2026. Dokument jest podstawą do wygenerowania makiety programu (rozdział 9 to gotowa
lista elementów każdego ekranu) oraz decyzji: co jest w becie, co później, co jest premium, czy zmieniać
logo. Uzupełnia „Wytyczne GUI i marki” (kolory, typografia, komponenty), nie powtarza ich.

## 1. Zasada: program zaplanowany na wiele gier

Beta obsługuje F1 25 i 2026 Season Pack, ale szkielet okna i danych od pierwszego dnia zakłada inne gry
z telemetrią (Assetto Corsa Competizione, iRacing, Le Mans Ultimate, rFactor 2, Automobilista 2, F1 26).
Gracz w becie tego nie widzi; przełącznik gry pojawi się dopiero, gdy będzie druga gra.

Co to znaczy w praktyce:

- **Adapter gry**: jedna warstwa między grą a resztą programu. Dla każdej gry: skąd telemetria (UDP, pamięć współdzielona, plik), jak wykryć sesję i tor, jak nazywają się asysty i jakie są ich poziomy, jakie tory i auta istnieją. Reszta programu widzi tylko „okrążenie, zakręt, prędkość, gaz, hamulec, bieg, asysty, bateria, opony”.
- **Identyfikatory z prefiksem gry**: tor to `f1_25:11`, nie `11`; plik toru, kształt i baza mają pole `game`. Dzięki temu Monza z F1 25 i Monza z ACC to dwa różne tory z osobnym postępem.
- **Reguły trenera parametryzowane** na gry: te same reguły hamowania i gazu, ale progi i słownictwo asyst z adaptera (w ACC nie ma „kroków TC 0–2”, jest skala 0–11; w iRacing nie ma ERS).
- **Nazewnictwo w oknie bez marki gry**: „Gra połączona”, nie „F1 25 połączona”; „Tryb nauki”, nie „Time Trial”. Nazwa gry pojawia się tylko w pastylce stanu i w ustawieniach.
- **Ukryte na razie**: Ustawienia → Gra → wybór gry (tylko F1 25, lista jednoelementowa, pole wyszarzone, bez zmian układu po dodaniu kolejnych); w Karcie kierowcy miejsce na „Gry: F1 25”; w Analizie i Postępie filtr gry, widoczny dopiero przy dwóch grach.
- **Słownik treści** (teksty trenera, lekcje, nazwy zakrętów) w plikach danych per gra, nie w kodzie.

## 2. Co program zawiera w becie, co później

| Obszar | Beta (teraz) | Później (po becie) |
| --- | --- | --- |
| Gry | F1 25, 2026 Season Pack, oba formaty telemetrii | ACC, iRacing, LMU, F1 26; wybór gry w ustawieniach |
| Trener głosowy | 9 reguł hamowania/gazu/biegu/przyczepności, komunikat po zakręcie i po okrążeniu, nacisk bez TC/ABS, ERS, kroki asyst, cel na okrążenie | tryb „wytłumacz mi”, lekcje z jednym celem, optymalny punkt hamowania i gazu z celem „5 m później”, DRS, plan baterii |
| Okno | kreator, Start z sesją na żywo i plakietką kierowcy, Postęp, Karta kierowcy, Ustawienia, samouczek w dymkach | Analiza z wykresami i mapą, Lekcje, Odznaki, Słownik, lektor samouczka, język angielski |
| Nakładka | okrążenie, zakręt, popraw, 3 zdania, cel, stan | mapa toru z punktem hamowania, delta na żywo |
| Dane | baza lokalna, nagrania, dziennik, recorder kształtu toru, raport błędu ZIP | konto w chmurze, synchronizacja, ranking, udostępnianie okrążeń |
| Tory | Bahrajn, Monza, Suzuka (pliki); inne tory: tylko tabela po sesji | wszystkie tory F1 z recordera i automatycznego wykrywania; kształty na mapie |
| Tryb wyścigowy | teksty inżyniera gotowe, tryb wyszarzony w oknie | inżynier: opony, pit, flagi, SC, odstępy, uszkodzenia, deszcz; start i walka; komendy głosowe |
| Eksport | podsumowanie w oknie, log | raport PDF przez okno drukowania Windows, CSV telemetrii |
| Wydanie | `.exe` jednym plikiem, aktualizacja ręczna | sprawdzanie aktualizacji, podpis kodu, instalator |

Zasada doboru: w becie jest wszystko, co sprawia, że początkujący po pierwszej sesji wie, co poprawić, i
widzi, że robi postęp. Nic, co wymaga chmury, konta albo drugiej gry.

## 3. Plakietka kierowcy na ekranie Start

Karta kierowcy jest zawsze widoczna na ekranie Start, po prawej stronie, jako plakietka w stylu prawa
jazdy. Kliknięcie otwiera pełną Kartę kierowcy.

![Plakietka kierowcy (prawa kolumna ekranu Start)](assets/brand/plakietka-kierowcy.png)

Zawartość plakietki (stała, bez przewijania): nagłówek „BOXBOX ACADEMY / LICENCJA KIEROWCY” ze znakiem,
poziom licencji w cyjanie (L1–L4 = krok asyst: L1 automat i pełne asysty, L2 TC średnia, L3 TC wyłączona,
L4 bez TC i ABS), zdjęcie w kole, nick, ID kierowcy, cztery wiersze: krok asyst, tory (ile jeździ i ile
opanował), okrążenia, seria czystych; pasek do następnego kroku z podpisem; data dołączenia.
Poziom licencji liczy się z najwyższego kroku osiągniętego na dowolnym torze. Plakietka nie ma przycisków.

## 4. Wersja darmowa i premium

Zasada: wersja darmowa jest pełnym trenerem, nie wersją demo. Premium daje głębię i wygodę, nie odblokowuje
tego, co trener mówi. Gracz, który nigdy nie zapłaci, ma się poprawiać i polecać program.

| Funkcja | Darmowa | Premium „Pit Crew” |
| --- | --- | --- |
| Trener głosowy, wszystkie reguły, wszystkie tory i obie gry | tak | tak |
| Kroki asyst, cel na okrążenie, plakietka i licencja | tak | tak |
| Nakładka | tak | tak + mapa toru z punktem hamowania i deltą na żywo |
| Kreator, samouczek, słownik pojęć | tak | tak |
| Postęp: krok, seria, zakręty opanowane, tabela przejazdów | tak | tak + trendy, porównanie miesiąc do miesiąca, odznaki rozszerzone |
| Historia sesji | ostatnie 30 dni | bez limitu |
| Analiza: wykres prędkości, gazu i hamulca jednego okrążenia na tle referencji | tak | tak + delta czasu, bieg, kierownica, ERS, mapa z punktami hamowania, porównanie dwóch dowolnych okrążeń, znaczniki uwag |
| Raport sesji | podsumowanie w oknie | PDF przez okno drukowania i CSV telemetrii |
| Lekcje | 3 lekcje startowe (hamowanie, gaz na wyjściu, czyste okrążenie) | pełny plan lekcji, lekcje per zakręt, tryb „wytłumacz mi” rozszerzony |
| Referencje | własne najlepsze, duch Time Trial | biblioteka okrążeń wzorcowych na każdy tor (od szybkich graczy), optymalny punkt hamowania i gazu |
| Tryb wyścigowy (inżynier) | podstawowy: pit, flagi, SC | pełny: opony z prognozą, odstępy, uszkodzenia, deszcz, start i walka, komendy głosowe |
| Głos | mechanik (Piotr) | dodatkowe głosy i lektor samouczka, wybór tonu (spokojny / zdecydowany) |
| Nowe gry i tory | po premierze | wcześniejszy dostęp i głos w kolejności |
| Ranking (po becie) | podgląd | udział z plakietką |

Cena: jeden próg miesięczny w okolicach ceny jednej pizzy i roczny z dwoma miesiącami gratis; na Patreonie
te same progi plus „Kibic” (wsparcie bez funkcji, podziękowanie w aplikacji). W becie wszystko jest
darmowe, a premium pojawia się z wersją 1.0; testerzy bety dostają rok premium.

## 5. Logo: analiza i zalecenie

Obecne logo (bolid z przodu, fala dźwięku, napis „BoxBox” na tabliczce, „ACADEMY” pod spodem) ma dobry
pomysł: auto + głos = trener na radiu. Trzy rzeczy są przeciw niemu:

1. **Nie skaluje się.** Przy 32 px (ikona na pasku zadań, favicon, awatar na Patreonie) bolid, fala i napis zlewają się w plamę. Marka potrzebuje znaku, który działa od 16 px do billboardu.
2. **Styl renderu 3D** (połysk, fazy, chrom na literach, rozmycia) nie pasuje do płaskiego, spokojnego interfejsu z wytycznych i wygląda jak typowy obraz z generatora. To osłabia wrażenie profesjonalizmu, na którym nam zależy.
3. **Brak wersji**: nie ma znaku bez tekstu, wersji jednokolorowej (do druku, znaku wodnego, haftu), poziomej z tekstem obok, ani pliku wektorowego.

Zalecenie: **zmienić wykonanie, zostawić pomysł.** Nowy system logo:

- **Znak**: bolid z przodu uproszczony do kilku kształtów (opony, skrzydło, halo) zrośnięty z falą dźwięku, która przechodzi w linię toru. Dwa kolory na ciemnym tle: biały kształt, cyjanowa fala; akcent czerwony jedna kreska (skrzydło). Czytelny w jednym kolorze.
- **Napis**: „BoxBox” w geometrycznym, lekko pochylonym kroju bez szeryfów (np. Exo 2, Rajdhani, Montserrat Alt), dwa „Box” w tym samym kolorze (biel), bez chromu; „ACADEMY” rozstrzelone pod spodem w Ash. Wariant poziomy: znak po lewej, napis po prawej.
- **Warianty**: pełne pionowe, poziome, sam znak, jednokolorowe białe i czarne, ikona 16/32/48/256 px, SVG + PNG.

Gdzie zrobić profesjonalnie, w kolejności opłacalności:

1. **Projektant wektorowy** (Useme, Fiverr, 99designs; szukaj „logo wektorowe esport/motorsport”, portfolio z płaskimi znakami): 300–800 zł, brief = ten rozdział plus paleta z wytycznych. Wynik: SVG, warianty, krótka księga znaku. To najlepsza opcja w budżecie 3000 zł.
2. **Generator wektorowy + poprawki**: Recraft (generuje SVG), Ideogram (dobrze pisze tekst), potem porządek w Figmie albo Inkscape. Tanio, ale wymaga ręcznego czyszczenia; nadaje się do szkiców dla projektanta.
3. **Looka / Brandmark**: szybko, pakiet z wariantami, ale wygląda generycznie; traktować jako plan awaryjny.

Dopóki nowe logo nie powstanie, obecne zostaje w oknie i materiałach; zmiana to podmiana plików
w `assets/` bez zmian w kodzie.

## 6. Funkcje, których jeszcze nie było w planie, a warto dodać (propozycja Claude)

- **Jedno zdanie po sesji**: „Dziś: T1 o 0,4 s lepiej niż tydzień temu” na ekranie Start, zawsze jedna pochwała i jedna rzecz do pracy.
- **Tryb „cicho”**: trener mówi tylko po okrążeniu (dla graczy, których rozprasza głos w trakcie), przełącznik na Start.
- **Przypomnienie o asystach**: gdy gra zgłasza inne asysty niż krok, do którego gracz doszedł („masz TC pełną, a jesteś na kroku 3; wracasz celowo?”), bez karania.
- **Raport błędu jednym przyciskiem**: pakuje dziennik, bazę, ostatnie nagranie i ustawienia do ZIP (mechanizm recordera), gracz wysyła plik.
- **Słownik pojęć** z tymi samymi tekstami, które trener mówi w trybie „wytłumacz mi”.
- **Tryb pada**: nawigacja po oknie strzałkami i Enterem, bo wielu początkujących gra na padzie bez myszy pod ręką.
- **Plakietka do udostępnienia**: eksport plakietki kierowcy jako PNG ze stemplem marki (materiał do social mediów i Patreona, darmowa reklama).
- **Sesja offline**: przegląd Postępu i Analizy bez gry i bez internetu, zawsze.
- **Zgoda na dane**: jedno pytanie w kreatorze, czy anonimowe liczby (tory, czasy, kroki) mogą trafić do przyszłego rankingu; domyślnie nie.

## 7. Co w programie jest już gotowe (stan kodu 27.10)

Silnik: telemetria obu formatów, zakręty, okrążenia, 9 reguł, trener na żywo, ERS, kroki asyst, baza,
694 klipy głosu z radiem, recorder kształtu toru, dziennik. Okno 0.6.0: Start z sesją na żywo, kreator,
Karta kierowcy (bez plakietki na Start), Postęp z tabelą, Ustawienia, samouczek, nakładka Qt, `.exe`.
Do zrobienia w oknie według wytycznych: przebudowa wyglądu, plakietka na Start, pastylka stanu w
nagłówku, przełączniki, ikony, Analiza.

## 8. Mapa ekranów

```
Kreator (raz) -> Start <-> Sesja na żywo -> Podsumowanie sesji -> Analiza
                 |-- Postęp (tor -> krok, trend, zakręty, tabela, odznaki)
                 |-- Lekcje (lista -> lekcja -> sesja z celem)
                 |-- Karta kierowcy (pełna; z plakietki na Start)
                 |-- Ustawienia (Dźwięk, Nakładka, Gra [ukryte: wybór gry], Dane, Pomoc)
                 `-- Pomoc: słownik, samouczek, raport błędu
Nakładka (osobne okno nad grą, bez przycisków)
```

## 9. Rozpiska elementów każdego ekranu (do makiety)

Układ wspólny: lewa nawigacja 240 px (logo, pozycje: Start, Analiza, Postęp, Lekcje, Karta kierowcy,
Ustawienia; na dole Pomoc i wersja), nagłówek strony (tytuł, jedno zdanie, po prawej pastylka stanu
gry), treść w kartach. Wszystkie teksty poniżej są docelowymi tekstami w programie.

### 9.1 Kreator pierwszego uruchomienia

1. Tytuł „Pierwsze uruchomienie”, pasek postępu 4 kroków z nazwami: Telemetria, Głośniki, Asysty, Kierowca.
2. Krok Telemetria: tabela 7 ustawień gry (Telemetria UDP: Wł.; Tryb rozgłaszania: Wył.; Adres IP: 127.0.0.1; Port: 20777; Częstotliwość: 60 Hz; Format: 2025 albo 2026; Twoja telemetria: Publiczna), przycisk „Sprawdź (nasłuch 5 s)”, pole wyniku: „Jest telemetria: Monza, format 2025, 60 pakietów/s” / „Nic nie dotarło…” / „Port zajęty…”.
3. Krok Głośniki: zdanie instrukcji, przyciski „Odtwórz powitanie”, „Słyszę”, „Nie słyszę”, pole podpowiedzi.
4. Krok Asysty: tabela zaleceń (Skrzynia: automatyczna; TC: pełna; ABS: włączony; Linia jazdy: pełna; Asysta ERS: wyłączona; Flashback: nie używaj), zdanie „Trener powie, kiedy co zdjąć”.
5. Krok Kierowca: pole „Nick”, pole zdjęcia (przeciągnij), przełącznik „Anonimowe statystyki do przyszłego rankingu” (domyślnie wyłączony), przycisk „Zakończ i przejdź do startu”.
6. Dół: „Wstecz”, „Dalej”.

### 9.2 Start (stan: przed sesją)

1. Nagłówek: „Start”, podpis „Trener na radiu: włącz telemetrię w grze, wyjedź na tor i naciśnij Jedź.”, pastylka stanu (zielona „Gra połączona · Monza · 60 pakietów/s” / szara „Czekam na grę” / czerwona „Port 20777 zajęty”).
2. Karta akcji (lewa, szeroka): przełącznik trybu „Nauka | Wyścig” (Wyścig wyszarzony z dopiskiem „wkrótce”), pole „Nazwa sesji”, przełączniki „Nagrywaj sesję”, „Nakładka na grze”, „Tryb cicho (uwagi tylko po okrążeniu)”, przycisk JEDŹ (jedyny czerwony).
3. Plakietka kierowcy (prawa kolumna, 320 px): jak w rozdziale 3.
4. Karta „Ostatnio” (pod akcją): jedno zdanie podsumowania ostatniej sesji („Wczoraj, Monza: najlepsze 1:24.279, do pracy T8–T10 gaz za wcześnie”), przycisk „Zobacz analizę”.
5. Karta „Dziś do zrobienia” (pod plakietką): cel kroku („3 czyste okrążenia z rzędu, masz 2”), aktywna lekcja, przycisk „Zacznij lekcję”.

### 9.3 Start (stan: sesja na żywo)

1. Karta akcji zmienia się w pasek: nazwa sesji, czas trwania, „nagrywam”, przycisk „Zakończ sesję” (zwykły, nie czerwony).
2. Panel na żywo (lewa, duża karta): „OKRĄŻENIE 4” (dopisek „pit lane” / „nieważne”), zakręt w cyjanie „T8–T10” + „za 120 m” / „TERAZ”, bursztynowa linia „Na tym okrążeniu popraw: T1–T2, hamuj 20 m wcześniej”, linia podziału, trzy ostatnie zdania mechanika z czasem (najnowsze pogrubione), karta celu z paskiem „Cel: 3 czyste okrążenia z rzędu · 2/3”.
3. Prawa kolumna: wykres „Prędkość · ostatnie okrążenie vs najlepsze” (cyjan vs szary), trzy kafelki: „Najlepsze dziś 1:24.279”, „Do referencji −0,41 s” (zielony), „Okrążenia 4”; karta stanu: „Obciążenie 1,2 % · nagrywam monza-sroda.bin · 60 Hz”, „Esc na nakładce albo Zakończ sesję w tym oknie”.
4. Plakietka kierowcy schowana na czas sesji (wraca po zakończeniu).

### 9.4 Podsumowanie sesji (po Zakończ)

1. Tytuł „Podsumowanie: Monza, 6 okrążeń, 14:32”.
2. Dwie karty obok siebie: „Dobrze” (jedno zdanie, zielone, np. „T4–T5 hamujesz 15 m później niż tydzień temu”) i „Do pracy” (jedno zdanie, bursztynowe).
3. Tabela okrążeń: numer, czas, delta do najlepszego, ważne, uwagi (liczba), przycisk „Analiza” w wierszu.
4. Tabela zakrętów najlepszego okrążenia: zakręt, v_min, bieg, hamowanie, pełny gaz, Δ czasu (monospace).
5. Pasek postępu kroku i ewentualny komunikat „Trzy czyste z rzędu: kolejny krok TC wyłączona” z przyciskiem „Pokaż, jak to ustawić w grze”.
6. Przyciski: „Zobacz analizę”, „Drukuj raport (PDF)” (premium), „Nowa sesja”.

### 9.5 Analiza

1. Nagłówek z wyborem: lista sesji (data, tor, liczba okrążeń), lista okrążeń sesji, przełącznik „Porównaj z: najlepsze / duch / wybrane okrążenie”.
2. Kolumna wykresów ze wspólną osią dystansu: prędkość; gaz i hamulec; bieg; kierownica; delta czasu (premium: bieg, kierownica, delta). Linia gracza cyjan, referencja szara, różnica zielona/czerwona.
3. Mapa toru (karta pod wykresami): obrys z kształtu, zakręty z numerami, punkty hamowania gracza (czerwone kropki) i referencji (szare), strefy DRS; kliknięcie zakrętu przewija wykresy.
4. Lista uwag trenera z tego okrążenia (zakręt, uwaga, strata w s), kliknięcie zaznacza miejsce na wykresie.
5. Przyciski: „Eksport CSV”, „Drukuj (PDF)”, „Ustaw jako referencję”.

### 9.6 Postęp

1. Wybór toru (pastylki z nazwami torów, aktywny z czerwonym paskiem); ukryty filtr gry.
2. Karta kroku: „Krok 2: TC średnia”, pasek „czyste okrążenia z rzędu 2/3”, „następny krok: TC wyłączona”.
3. Wykres trendu: czasy ostatnich 20 okrążeń, najlepszy zaznaczony, linia kroku asyst.
4. Dwie listy pastylek: „Zakręty opanowane” (zielone) i „Do pracy” (bursztynowe z opisem po polsku: „T8–T10: gaz za wcześnie”).
5. Rząd odznak (szare = do zdobycia, kolorowe = zdobyte): Pierwsze czyste okrążenie, Bez TC, 10 sesji, Tor opanowany, Seria 7 dni.
6. Tabela przejazdów: Data, Okrążenie, Czas, Δ, Ważne, TC, ABS, Skrzynia, Uwagi; sortowanie po nagłówku.

### 9.7 Lekcje

1. Lista kart lekcji: tytuł, jedno zdanie celu, czas („5 okrążeń”), stan (nowa / w toku 2/5 / zaliczona), etykieta „Premium” na zablokowanych.
2. Lekcja: opis z rysunkiem zakrętu, cel mierzalny („hamuj w T1 10 m później niż dziś, 3 razy z rzędu”), przycisk „Zacznij” (uruchamia sesję z celem; trener mówi tylko o tym zakręcie).
3. Lekcje startowe (darmowe): Hamowanie w jednym zakręcie, Gaz na wyjściu, Czyste okrążenie.

### 9.8 Karta kierowcy (pełna)

1. Plakietka w powiększeniu (jak 9.2) z przyciskiem „Zapisz plakietkę jako obraz” (ze stemplem marki).
2. Pola: Nick, zdjęcie (przeciągnij albo przeglądarka plików w stronie), ID (tylko do odczytu), „od 10.2026”.
3. Kafelki: Sesje, Okrążenia, Tory, Godziny na torze.
4. Lista torów: nazwa, najlepszy czas, krok, zakręty opanowane/wszystkie, ostatnia sesja.
5. Sekcja „Gry” (ukryta w becie): F1 25.
6. Przełącznik „Anonimowe statystyki do rankingu”.

### 9.9 Ustawienia

1. Dźwięk: suwak głośności z „Odtwórz próbkę”, przełącznik „Tryb cicho”, wybór głosu (jeden, reszta „Premium”).
2. Nakładka: włączona, skala, krycie, „Pokaż podgląd” (pokazuje nakładkę na 5 s), pozycja zapamiętana.
3. Gra: pastylka wykrytej gry i formatu, port UDP, pole „Gra” (lista z jedną pozycją F1 25, wyszarzona), „Sprawdź telemetrię” (jak w kreatorze).
4. Dane: folder nagrań, „Nagrywaj sesje domyślnie”, historia (30 dni / bez limitu premium), „Wyślij raport błędu” (pakuje ZIP i pokazuje ścieżkę).
5. Pomoc: „Samouczek jeszcze raz”, „Kreator jeszcze raz”, „Słownik pojęć”, wersja, licencje, „Sprawdź aktualizację” (później).

### 9.10 Nakładka

Okno 600 px, ramka czerwona 3 px, bez przycisków, kolejność: OKRĄŻENIE N; zakręt + metry; popraw;
trzy zdania mechanika; cel z paskiem; linia stanu (prędkość, bieg, dystans, nagrywanie). Premium: mała
mapa toru z punktem auta i znacznikiem hamowania w prawym górnym rogu.

### 9.11 Słownik i raport błędu

Słownik: lista haseł (trail-braking, apeks, delta, deploy ERS, krok asyst, okrążenie referencyjne),
każde z dwoma zdaniami i rysunkiem. Raport błędu: jedno zdanie, co się stało (pole tekstowe), przycisk
„Zapakuj”, wynik: ścieżka ZIP i „Wyślij ten plik na adres …”.

## 10. Gotowy opis dla generatora makiet

Tekst do wklejenia do narzędzia generującego makiety (po polsku; jeśli narzędzie wymaga angielskiego, przetłumacz 1:1):

```
Aplikacja desktopowa Windows „BoxBox Academy”: trener jazdy do gier wyścigowych z telemetrią,
dla początkujących. Styl: ciemny, płaski, bez gradientów i cieni; tło #0B0C0E, karty #15171B,
pola #1F232A, tekst #F4F5F7, podpisy #9BA3AD, jedna czerwona akcja #E8232A, dane na żywo #19E6E6,
postęp #35D07F, ostrzeżenie #FFC43D. Czcionka Segoe UI, liczby Consolas. Siatka 8 px, karty
zaokrąglone 16 px. Lewa nawigacja 240 px z logo i pozycjami: Start, Analiza, Postęp, Lekcje,
Karta kierowcy, Ustawienia; na dole Pomoc. Nagłówek każdej strony: tytuł, jedno zdanie, po prawej
pastylka „Gra połączona · Monza · 60 pakietów/s” z zieloną kropką. Żadnych okien dialogowych:
błędy jako pasek w stronie. Ekrany: [wklej rozdziały 9.1–9.11].
```

## 11. Kolejność prac po makiecie

1. Przebudowa okna według wytycznych i makiety: Start z plakietką, pastylka stanu, przełączniki, ikony, panel na żywo (etap 6, dokończenie).
2. Analiza z wykresami i mapą z recordera (etap 7).
3. Lekcje i tryb „wytłumacz mi” (etap 8).
4. Podsumowanie sesji z „Dobrze / Do pracy”, odznaki (etap 10).
5. Nowe logo: brief do projektanta już teraz, podmiana plików gdy gotowe.
