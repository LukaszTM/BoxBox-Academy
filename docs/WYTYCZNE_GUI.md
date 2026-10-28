# BoxBox Academy – wytyczne GUI i marki

Wersja 1.0, 27.10.2026. Dokument dla każdego, kto projektuje, koduje albo publikuje cokolwiek pod marką
BoxBox Academy: okno aplikacji, nakładkę, stronę, grafiki na kanał i Patreon, e-maile.
Jedna zasada nad wszystkimi: **profesjonalnie, ale prosto dla kogoś, kto pierwszy raz siada do simracingu.**

## 1. Czym jest marka

BoxBox Academy to trener jazdy, który mówi do gracza jak mechanik na radiu: spokojnie, konkretnie, bez
krzyku. Marka ma wyglądać jak pit wall zespołu F1 nocą: ciemno, czysto, jedno czerwone światło na
akcję i cyjanowe dane na żywo. Nie jest to gra, nie jest to stream, nie jest to arkusz telemetrii dla inżynierów.

Trzy słowa, którymi sprawdzamy każdą decyzję: **spokój** (nic nie miga, nic nie krzyczy), **jedna rzecz
naraz** (jedna akcja główna na ekranie, jedna uwaga trenera naraz), **postęp** (gracz zawsze widzi, co już
umie i co jest następne).

## 2. Kolory

Paleta pochodzi z logo (czerń, czerwień, cyjan, biel). Używamy dokładnie tych wartości; nic poza nimi.

![Paleta BoxBox Academy](assets/brand/paleta.png)

| Nazwa | Hex | Do czego |
| --- | --- | --- |
| Carbon | #0B0C0E | tło okna i każdej strony |
| Graphite | #15171B | panele, karty, pasek nawigacji |
| Steel | #1F232A | pola tekstowe, kafelki, element pod kursorem |
| Line | #2A2F37 | jedyna dozwolona linia podziału, 1 px |
| Chalk | #F4F5F7 | tekst główny |
| Ash | #9BA3AD | tekst drugorzędny, podpisy, osie wykresów |
| Signal Red | #E8232A | jedna akcja główna na ekranie (JEDŹ), błędy, logo |
| Telemetry Cyan | #19E6E6 | dane na żywo: zakręt, prędkość gracza na wykresie, ID kierowcy |
| Track Green | #35D07F | postęp, zaliczone, poprawa czasu |
| Pit Amber | #FFC43D | cel na okrążenie, ostrzeżenie, „popraw” |

Zasady koloru i stylu („nowoczesny”, nie „płaski”):

- Tło to gradient z głębią: granat #141A2E u góry przechodzi w grafit #0B0C0E u dołu, z dwiema miękkimi poświatami (czerwona w lewym górnym rogu, cyjanowa w prawym dolnym) i ledwo widocznymi liniami toru w tle. Nigdy jednolita czerń.
- Panele są ze szkła: półprzezroczyste (biel 16–20% krycia) z rozmyciem tła pod spodem, cienką jasną krawędzią (1 px, biel 15%), połyskiem na górnej krawędzi i miękkim cieniem pod spodem. Głębia bierze się z warstw, nie z ramek.
- Poświaty neonowe na tym, co ważne: zakręt i dane na żywo w cyjanie świecą, przycisk JEDŹ ma czerwoną łunę, pasek postępu i zielona delta świecą delikatnie. Jedna poświata na element, nigdy tekst zwykły.
- Czerwony tylko w jednym miejscu na ekranie: przycisk akcji głównej (gradient #FF3C42 → #E1232A). Gdy jest błąd, pasek błędu też jest czerwony, ale wtedy przycisk akcji jest wyłączony.
- Cyjan nigdy jako tło. Tylko tekst, linie danych i ich poświata.
- Zielony i bursztynowy tylko dla znaczenia (lepiej/gorzej, cel), nigdy ozdobnie.
- Ruch: przejścia między stronami 200 ms, pojawianie się kart z lekkim przesunięciem, liczby na żywo zmieniają się płynnie, nic nie miga.
- Tryb jasny nie istnieje.

![Makieta ekranu Start: docelowy wygląd (szkło, głębia, poświaty)](assets/brand/makieta-start-nowoczesna.png)

## 3. Typografia

| Rola | Krój | Rozmiar | Waga |
| --- | --- | --- | --- |
| Tytuł strony | Segoe UI (Windows), zapasowo Inter | 28 px | 700 |
| Nagłówek panelu | Segoe UI | 18 px | 600 |
| Tekst | Segoe UI | 15 px | 400 |
| Podpis, pomocniczy | Segoe UI | 13 px | 400, kolor Ash |
| Liczba na żywo (zakręt, okrążenie) | Segoe UI | 36–44 px | 800 |
| Tabele i telemetria liczbowa | Consolas, zapasowo DejaVu Sans Mono | 13 px | 400 |

Zasady: maksymalnie 3 rozmiary na jednym ekranie poza panelem na żywo; liczby w tabelach wyrównane do
prawej i w kroju o stałej szerokości; nigdy WIELKIE LITERY w zdaniach, tylko w krótkich etykietach stanu
(„OKRĄŻENIE 4”, „JEDŹ”); polskie znaki zawsze, bez skrótów typu „okr.”, chyba że w tabeli.

## 4. Siatka, odstępy, kształty

- Siatka 8 px: każdy odstęp to wielokrotność 8 (8, 16, 24, 32). Wewnątrz karty 24 px, między kartami 16 px, margines strony 32 px.
- Zaokrąglenia: karty 24 px, pola i przyciski 14 px, pastylki stanu pełne.
- Nawigacja po lewej 240 px, stała. Treść po prawej, maksymalnie 1160 px szerokości, dalej puste tło.
- Minimalne okno 1180 × 760. Przy mniejszym pokazujemy pasek przewijania, nie ściskamy.
- Elementy klikalne co najmniej 40 px wysokości. Gracz siedzi daleko od monitora albo używa pada.

## 5. Układ okna

Stałe elementy:

1. **Nawigacja** (lewa kolumna): logo u góry, pięć pozycji w stałej kolejności: Start, Analiza, Postęp, Karta kierowcy, Ustawienia. Aktywna pozycja: tło Steel i czerwony pasek 4 px z lewej. Pod spodem wersja.
2. **Nagłówek strony**: tytuł 28 px i jedno zdanie podpisu w Ash. Po prawej pastylka stanu połączenia z grą: zielona kropka i „Gra połączona · Monza · 60 pakietów/s”, szara „Czekam na grę”, czerwona „Port zajęty”. Pastylka jest na każdej stronie, zawsze w tym samym miejscu.
3. **Treść**: karty Graphite na tle Carbon. Nigdy więcej niż 3 karty w rzędzie.
4. **Pasek błędu**: wewnątrz strony, nad treścią, czerwona ramka 1 px na tle Graphite, tekst i krzyżyk. Żadnych wyskakujących okien, nigdy, w całym programie. Wybór pliku, potwierdzenia, błędy, ustawienia: wszystko wewnątrz strony.
5. **Samouczek**: dymki w oknie (ramka Signal Red, tło ciemnoczerwone), jeden naraz, z licznikiem „Samouczek 2/7”, przyciskami Dalej i Zamknij. Pojawia się przy pierwszym uruchomieniu po kreatorze; do włączenia ponownie w Ustawieniach.

## 6. Ekrany i ich zawartość

### Kreator pierwszego uruchomienia (tylko raz)

Cztery kroki z paskiem postępu: Telemetria (tabela ustawień gry i przycisk Sprawdź, który nasłuchuje 5 s i
mówi, co jest nie tak), Głośniki (Odtwórz, Słyszę, Nie słyszę z podpowiedzią), Asysty (zalecane
ustawienia na start z wyjaśnieniem, że trener powie, kiedy co zdjąć), Kierowca (nick). Po zakończeniu
przechodzi na Start i uruchamia samouczek. Kreator nigdy nie blokuje: można go przerwać i wrócić z Ustawień.

### Start

Karta akcji: tryb (Nauka / Wyścig), nazwa sesji, przełączniki Nagrywaj i Nakładka, przycisk JEDŹ.
Panel na żywo (duży, po lewej): numer okrążenia, zbliżający się zakręt w cyjanie z metrami, bursztynowa
linia „Na tym okrążeniu popraw”, trzy ostatnie zdania mechanika z czasem (najnowsze pogrubione), na dole
cel z paskiem postępu. Po prawej: wykres prędkości ostatniego okrążenia na tle najlepszego, trzy kafelki
(najlepsze dziś, delta do referencji, liczba okrążeń), linia obciążenia i nagrywania. Po sesji panel
zamienia się w podsumowanie: tabela zakrętów i przycisk Zobacz analizę.

### Analiza (etap 7)

Wybór sesji i okrążenia u góry (lista, nie okno). Wykresy w jednej kolumnie, wspólna oś dystansu:
prędkość, gaz i hamulec na jednym wykresie, bieg, kierownica, delta czasu. Linia gracza w cyjanie,
referencja w Ash. Pod wykresami mapa toru z zakrętami i punktami hamowania; kliknięcie zakrętu przewija
wykresy do niego. Uwagi trenera jako znaczniki na osi. Przyciski: Porównaj z (druga linia), Eksport CSV,
Drukuj PDF (systemowe okno drukowania Windows, jedyny wyjątek od zasady „bez osobnych okien”, bo jest systemowe).

### Postęp

Wybór toru. Karta kroku asyst z paskiem serii (2/3). Trend czasów na wykresie (ostatnie 20 okrążeń,
najlepszy zaznaczony). Zakręty opanowane (zielone pastylki) i do pracy (bursztynowe z nazwą reguły po
polsku, nie `throttle_late`). Tabela przejazdów z filtrami. Odznaki (etap 10) jako rząd kafelków.

### Karta kierowcy

Zdjęcie w kole 160 px, nick 28 px, ID w cyjanie 15 px pod spodem, mniejsze niż teraz. Trzy kafelki
liczbowe, lista torów z najlepszym czasem i krokiem. Zdjęcie przez przeciągnięcie albo przeglądarkę
plików wbudowaną w stronę. Przycisk Zapisz jeden, na dole karty.

### Ustawienia

Grupy: Dźwięk (głośność z podglądem Odtwórz), Nakładka (włączona, skala, pozycja: przycisk Pokaż
podgląd), Gra (port, format wykryty automatycznie), Dane (folder nagrań, wyślij raport błędu: pakuje
dziennik, bazę i ostatnie nagranie przez recorder), Pomoc (samouczek ponownie, kreator ponownie, wersja, licencje).

### Nakładka na grze

Okno bez ramki, 600 px szerokości, krycie 96%, ramka 3 px Signal Red, zawsze na wierzchu, przeciągane.
Zawartość i kolejność dokładnie jak w panelu na żywo: okrążenie, zakręt, popraw, trzy zdania, cel,
pasek stanu. Nic więcej. Żadnych przycisków na nakładce; zamyka się z okna albo klawiszem Esc.

## 7. Komponenty

| Komponent | Wygląd | Zasada |
| --- | --- | --- |
| Przycisk główny | gradient czerwieni, czerwona łuna, biały tekst 800, 72 px wysokości, 18 px zaokrąglenie | jeden na ekranie |
| Przycisk zwykły | tło Steel, tekst Chalk, bez obramowania; pod kursorem jaśniejsze tło, nie czerwona ramka | dowolna liczba, ale grupowane |
| Przełącznik | pastylka 44 × 24, zielona gdy włączony | zamiast pól wyboru z ptaszkiem |
| Pole tekstowe | tło Steel, 44 px, bez ramki, etykieta nad polem w Ash | podpowiedź w polu tylko, gdy etykieta nie wystarcza |
| Karta | szkło: biel 18% z rozmyciem tła, krawędź biel 15% 1 px, cień miękki, 24 px zaokrąglenie, 24 px wnętrze | nigdy jednolite tło |
| Kafelek liczbowy | liczba 24–28 px 700 nad podpisem 13 px Ash | kolor liczby tylko gdy ma znaczenie (zielony lepiej) |
| Pastylka stanu | tło Steel, kropka koloru stanu, tekst 15 px | kolory: zielony/szary/czerwony |
| Tabela | nagłówek Steel 600, wiersze 36 px, linie Line 1 px tylko poziome, liczby monospace do prawej | sortowanie po kliknięciu nagłówka, bez ramki zewnętrznej |
| Wykres | tło karty, osie Ash 1 px, siatka Line kropkowana, linia gracza Cyan 2 px, referencja Ash 1,5 px, obszar różnicy zielony/czerwony 20% krycia | legenda nad wykresem, nie obok |
| Pasek postępu | 12 px, tło Line, wypełnienie Track Green, zaokrąglony | zawsze z liczbą obok („2 / 3”) |
| Pasek błędu | ramka Signal Red 1 px, tło Graphite, ikona, tekst, krzyżyk | w stronie, nad treścią |
| Dymek samouczka | ramka Signal Red 2 px, tło #2B1D1E, 360 px | jeden naraz |

## 8. Ikony

Jeden zestaw na całą markę: **Lucide** (licencja ISC, darmowa także komercyjnie), styl liniowy, grubość
kreski 1,75 px, rozmiar 20 px w nawigacji i 16 px w przyciskach, kolor dziedziczony z tekstu. Nie
mieszamy z emoji ani ikonami wypełnionymi. Przypisania: Start = `play`, Analiza = `line-chart`, Postęp =
`trending-up`, Karta kierowcy = `id-card`, Ustawienia = `settings`, połączenie = `radio`, nagrywanie =
`circle-dot`, nakładka = `picture-in-picture-2`, błąd = `alert-triangle`, cel = `target`, pit = `wrench`.
Ikona aplikacji: `assets/icon.ico` ze znaku (bolid i fala), bez tekstu.

## 9. Język w interfejsie

- Per „ty”, krótko, bez wykrzykników. Mechanik mówi tak samo w głosie, w oknie i w e-mailu.
- Czasowniki na przyciskach: JEDŹ, Zakończ sesję, Sprawdź, Zapisz, Zobacz analizę. Nie „OK”, nie „Anuluj”.
- Błędy mówią, co zrobić, nie co się stało w kodzie: „Port 20777 zajęty: zamknij inny program z telemetrią”.
- Pojęcia techniczne (trail-braking, delta, deploy) mają w aplikacji słownik; pierwsze wystąpienie ma dymek z wyjaśnieniem.
- Nazwy reguł nigdy po angielsku w oknie (`throttle_late` → „pełny gaz za późno”).

## 10. Zasady dla początkującego

1. Ekran Start po kreatorze ma dokładnie jedną rzecz do zrobienia: JEDŹ. Reszta jest domyślnie ustawiona dobrze.
2. Każda liczba ma podpis, każda delta ma znak i kolor. Gracz nie musi wiedzieć, co to v_min.
3. Postęp jest widoczny na każdym ekranie: pastylka „krok 2 · 2/3 czystych” w nagłówku Start i Postęp.
4. Nic nie znika i nic nie wyskakuje. Stan zmienia się w miejscu.
5. Po sesji zawsze jest jedna pochwała i jedna rzecz do poprawy, nie lista dziesięciu uwag.

## 11. Materiały marki (gotowe w `assets/brand/`)

- `paleta.png`: paleta do wklejenia w Figmę lub do grafika.
- `znak-wodny.png`: logo z kryciem 32% na przezroczystym tle, do nakładania na zrzuty i filmy; `znak-wodny-znak.png`: sam znak (bolid i fala) 25%, do tła miniatur.
- `makieta-start-nowoczesna.png`: docelowy wygląd ekranu Start (szkło, głębia, poświaty), wzorzec dla kodu; `makieta-start.png`: wcześniejsza wersja płaska, nieaktualna.
- `email.html` i `email.txt`: szablon e-maila (ciemne tło, baner, jeden czerwony przycisk, stopka z oznaczeniem marki i zastrzeżeniem o EA/F1); pola `{{ }}` do podmiany; `przyklad-stempla.png`: jak wygląda ostemplowana grafika.
- Stemplowanie grafik do publikacji: `python tools/brand_assets.py stempluj plik.png` wkleja logo w prawym dolnym rogu (18% szerokości, 85% krycia). Każdy zrzut, miniatura i film przed publikacją przechodzi przez stempel.
- Baner `assets/banner.png` (1024 × 359) do nagłówków kanału i Patreona; logo `assets/logo.png` (wektor, koncepcja 2 z 28.10.2026, źródła w `assets/logo-src/v2/`) tylko na ciemnym tle, na jasnym `logo-czarny.png`; minimalna szerokość logo 120 px; wokół logo pusta przestrzeń równa wysokości litery „B”.

Czego nie robimy: nie obracamy logo, nie zmieniamy jego kolorów, nie kładziemy na jasnym tle, nie piszemy
„Box Box” ani „BoxBox academy”; zawsze „BoxBox Academy”.

## 12. Budżet bety: 3000 zł

| Pozycja | Kwota | Po co |
| --- | --- | --- |
| Podpis kodu `.exe` (certyfikat OV, 1 rok) albo wersja na GitHub Releases z instrukcją dla antywirusa | 0–1200 zł | bez podpisu Windows ostrzega przy pierwszym uruchomieniu; to największa bariera dla nowego gracza. Zacznij bez podpisu, kup po pierwszych 50 pobraniach |
| ElevenLabs Creator, 2 miesiące | ok. 220 zł | dogrywki klipów trenera, inżynier, lekcje; potem wystarczy plan niższy |
| Domena i prosta strona (lista bety, pobieranie, Patreon) | ok. 150 zł/rok | adres w e-mailu i w grze; strona statyczna, bez kosztów hostingu |
| Grafik: 1 dzień pracy (ikony stanów, odznaki, karta kierowcy, miniatury na kanał w stylu makiety) | 600–800 zł | spójność, której kod sam nie zrobi |
| Testerzy: 3–5 początkujących, drobny bon za sesję testową z formularzem | 300 zł | formularz z `PLAN_TESTOW.md`, nagrania i opinie |
| Rezerwa (lektor do samouczka, druga para rąk przy `.exe` na czystym Windowsie) | reszta | nie wydawać przed betą |

Patreon: dwa progi wystarczą na start („Kibic” dostęp do bety i głos w kolejności torów, „Pit crew”
wcześniejsze wersje i własny tor dodany do planu). Treść dla patronów powstaje z tego, co i tak
robimy: nagrania sesji, raporty PDF, nowe tory. Patreon pobiera 8–12% plus opłaty, więc ceny w zł z zapasem.

## 13. Co zmienić w obecnym oknie (0.6.0) według tych wytycznych

Lista do wdrożenia w kodzie od razu, zanim powstanie Analiza:

- tło gradientowe z poświatami, panele ze szkła z cieniem, poświaty na danych na żywo i na JEDŹ,
- etykiety bez własnego tła, podpisy w Ash 13 px, tytuł strony 28 px,
- pola wyboru zamienić na przełączniki, pastylka stanu połączenia w nagłówku każdej strony,
- JEDŹ jako jedyny czerwony element; przyciski zwykłe bez czerwonej ramki pod kursorem,
- ikony Lucide w nawigacji, aktywna pozycja z czerwonym paskiem 4 px,
- panel na żywo w układzie z makiety (okrążenie, zakręt + metry obok, popraw, zdania z czasem, cel z paskiem),
- karta kierowcy: zdjęcie w kole, ID mniejsze, jeden przycisk Zapisz,
- tabela przejazdów: linie tylko poziome, liczby monospace do prawej, nazwy reguł po polsku,
- nakładka Qt: zawartość 1:1 z panelem na żywo, ramka 3 px, bez podpowiedzi o przeciąganiu w treści (tylko kursor).
