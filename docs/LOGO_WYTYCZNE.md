# Logo BoxBox Academy – wytyczne do przeróbki

Dokument dla projektanta (albo do samodzielnej pracy w generatorze wektorowym). Zawiera: ocenę obecnego
logo, co zostaje, co się zmienia, zasady nowego znaku, listę plików do oddania i test odbioru.

## 1. Ocena obecnego logo

Pomysł jest dobry i zostaje: bolid z przodu, fala dźwięku nad nim, nazwa na tabliczce. Czyta się jako
„auto + głos = trener na radiu”. Przeciw obecnemu wykonaniu są cztery rzeczy.

![Obecne logo w rozmiarach 500, 256, 128, 64 i 32 px. Od 64 px w dół bolid, fala i napis zlewają się w plamę.](docs/img/logo_obecne_skalowanie.png)

1. **Nie skaluje się.** Logo ma za dużo szczegółów: zawieszenie, halo, odblaski, 20 słupków fali, dwa kolory napisu, tabliczka z fazą. Przy 32 px (pasek zadań, zakładka przeglądarki, awatar na YouTube, Patreonie i Discordzie) nic nie da się rozpoznać. Marka potrzebuje znaku, który działa od 16 px.
2. **Styl renderu** (połysk, chrom na literach, fazy, cienie, rozmyte poświaty) nie pasuje do interfejsu programu, który jest szklany i nowoczesny, ale oparty na czystych kształtach. Taki render wygląda jak typowy obraz z generatora i osłabia wrażenie produktu zrobionego na serio.
3. **Brak systemu.** Jest jeden plik PNG. Nie ma: samego znaku bez tekstu, wersji poziomej, wersji jednokolorowej (druk, haft, znak wodny), wersji na jasne tło ani pliku wektorowego. Każde użycie poza oknem programu wymaga teraz kombinowania.
4. **Napis.** „BoxBox” w dwóch kolorach (biel i czerwień) dzieli nazwę na dwa słowa, a „ACADEMY” na osobnej tabliczce z cyjanowym paskiem to trzeci element graficzny. Nazwa ma być jednym słowem.

## 2. Co zostaje, co się zmienia

| Element | Zostaje | Zmienia się |
|---|---|---|
| Pomysł | bolid z przodu + fala dźwięku | — |
| Kolory | czerń, biel, Signal Red #E8232A, Telemetry Cyan #19E6E6 | bez gradientów, połysków i cieni |
| Nazwa | „BoxBox Academy” | jedno słowo „BOXBOX” w jednym kolorze; „ACADEMY” pod spodem, rozstrzelone, w Ash #9BA3AD |
| Bolid | sylwetka z przodu | uproszczony do czterech kształtów: dwie opony, halo, nos; skrzydło jako jedna czerwona kreska |
| Fala | po bokach bolidu | 4–5 słupków z każdej strony, zaokrąglone końce, w cyjanie; w wersji jednokolorowej te same słupki w kolorze znaku |
| Tabliczka | — | znika; napis stoi bez tła |
| Format | PNG | SVG jako źródło, PNG i ICO wygenerowane z SVG |

## 3. Zasady nowego znaku

![Szkic kierunku wykonany kodem, nie projekt końcowy. Projektant ma to zrobić lepiej, zachowując zasady z tego rozdziału.](docs/img/logo_szkic_kierunku.png)

1. **Geometria zamiast rysunku.** Znak składa się z prostych kształtów o jednakowej grubości linii. Wszystkie narożniki zaokrąglone tym samym promieniem. Żadnych odblasków, faz, cieni, gradientów.
2. **Dwa kolory plus akcent.** Biały kształt bolidu, cyjanowa fala, jedna czerwona kreska (przednie skrzydło). Nic więcej. Czerwień to akcent, nie drugi kolor główny.
3. **Działa w jednym kolorze.** Ten sam znak w samej bieli i w samej czerni musi być tak samo czytelny. To warunek dla znaku wodnego, haftu i druku jednobarwnego.
4. **Czytelny w 16 px.** Przy ikonie 16×16 widać trzy rzeczy: dwa koła, łuk halo i czerwoną kreskę. Jeśli projektant musi coś uprościć, upraszcza falę (mniej słupków), nie bolid.
5. **Napis.** „BOXBOX” wielkimi literami, krój zwężony, pogrubiony, lekko pochylony (6–10°), bez chromu i obrysów. Proponowany krój: **Barlow Condensed SemiBold Italic** (licencja OFL, ten sam krój co w HUD programu, więc marka trzyma się jednej typografii). Pod spodem „ACADEMY” w kroju Inter SemiBold, rozstrzelenie 0,4 em, kolor Ash. Nazwa pisana zawsze „BoxBox Academy” w tekście, „BOXBOX” tylko w logo.
6. **Proporcje.** Wersja pionowa: znak 2:1,5 (szerokość:wysokość), napis „BOXBOX” o szerokości 90 % znaku, „ACADEMY” o szerokości 60 % znaku. Wersja pozioma: znak po lewej, napis po prawej, wysokość napisu równa wysokości bolidu bez fali.
7. **Pole ochronne.** Wokół logo pusta przestrzeń równa wysokości litery „B” z napisu. Nic nie wchodzi w to pole: ani tekst, ani krawędź banera.
8. **Tło.** Logo projektowane na ciemne tło (Carbon #0B0C0E, Graphite #15171B). Na jasne tło wyłącznie wersja jednokolorowa czarna. Nigdy pełnokolorowe logo na bieli.

## 4. Warianty do oddania

| Kod | Wariant | Do czego |
|---|---|---|
| A | pełne pionowe (znak + BOXBOX + ACADEMY) | ekran startowy, materiały do publikacji, Patreon |
| B | poziome (znak po lewej, napis po prawej) | nagłówek okna, pasek boczny, baner kanału, stopka e-maila |
| C | sam znak | ikona programu, awatar, favicon, znak wodny na miniaturach |
| D | jednokolorowy biały (A, B, C) | znak wodny na zrzutach i filmach, haft, druk na ciemnym |
| E | jednokolorowy czarny (A, B, C) | jasne tło, druk, dokumenty |
| F | ikona Windows | 16, 24, 32, 48, 64, 128, 256 px w jednym pliku .ico; tło przezroczyste |

Pliki: SVG (źródło, tekst zamieniony na krzywe), PNG na przezroczystym tle w szerokościach 256, 512, 1024
i 2048 px dla każdego wariantu, ICO z rozmiarami jak wyżej, plus jedna strona PDF z polem ochronnym i
minimalnymi rozmiarami. Nazwy plików po polsku, bez spacji: `logo-pionowe.svg`, `logo-poziome.svg`,
`znak.svg`, `logo-pionowe-bialy.svg`, `znak-czarny.svg`, `ikona.ico`.

## 5. Minimalne rozmiary

| Wariant | Minimalna szerokość | Gdzie to sprawdzić |
|---|---|---|
| A pionowe | 120 px | plakietka kierowcy w programie |
| B poziome | 160 px | pasek boczny programu (zwinięty) |
| C znak | 16 px | ikona na pasku zadań Windows, zakładka przeglądarki |

## 6. Czego nie wolno

- Nie obracać znaku, nie rozciągać, nie zmieniać proporcji znaku i napisu względem siebie.
- Nie dodawać cieni, poświat, gradientów, obrysów ani tabliczek pod napisem.
- Nie zmieniać kolorów: tylko paleta z rozdziału 2 albo wersja jednokolorowa.
- Nie kłaść pełnokolorowego logo na jasnym tle ani na zdjęciu bez przyciemnienia.
- Nie używać logo F1, FIA, EA ani zespołów. Bolid ma być anonimowy: bez numerów, sponsorów i barw zespołu.

## 7. Test odbioru (projekt przyjmujemy, gdy wszystko przechodzi)

1. Znak C w 16×16 px na pasku zadań Windows: rozpoznawalne koła, halo i czerwona kreska.
2. Wersja D (biała) na zrzucie z gry przy kryciu 30 %: widać, że to ten sam znak.
3. Wersja E (czarna) wydrukowana na zwykłej drukarce w rozmiarze 2 cm: bez zlewania się kształtów.
4. Wersja B obok napisu „Krok 2 · TC średnia” w pasku bocznym programu: wysokość napisu równa wysokości tekstu interfejsu, logo nie dominuje nad treścią.
5. Plik SVG otwiera się w Inkscape i Figmie, tekst jest krzywymi, kolory to dokładnie wartości z palety.
6. Logo pokazane obok logo Trophy AI, SimHub i RaceLab wygląda jak produkt, nie jak obrazek z generatora.

## 8. Gdzie i za ile

| Droga | Koszt | Czas | Uwagi |
|---|---|---|---|
| Projektant wektorowy (Useme, Fiverr, 99designs; szukaj „logo wektorowe motorsport / esport”, portfolio z płaskimi znakami) | 300–800 zł | 5–10 dni | brief = ten dokument + plik palety `assets/brand/paleta.png`. Najlepsza opcja w budżecie 3000 zł. |
| Generator wektorowy + poprawki (Recraft generuje SVG, Ideogram dobrze pisze tekst), potem porządek w Inkscape | 0–100 zł | 1–2 dni własnej pracy | nadaje się na szkice do briefu; wynik końcowy i tak wymaga ręcznego czyszczenia krzywych |
| Looka / Brandmark | 100–300 zł | 1 dzień | pakiet wariantów od razu, ale wygląd generyczny; plan awaryjny |

Tekst do generatora (gdy robisz szkice sam):

```
Flat vector logo mark, front view of an open-wheel race car reduced to four simple
shapes: two tyres, halo arc, nose; front wing as a single red line (#E8232A).
Audio waveform bars on both sides in cyan (#19E6E6), rounded ends. White shapes on
dark background (#0B0C0E). No gradients, no shadows, no text, no gloss, equal stroke
width, rounded corners. Must be readable at 16 px. Minimal, geometric, motorsport.
```

## 9. Po otrzymaniu plików

Podmiana w programie to zamiana plików w `assets/` (`logo.png`, `mark.png`, `icon.png`, `icon.ico`,
`banner.png`) i w `assets/brand/` (znaki wodne, stempel) bez zmian w kodzie. Ikona w oknie i w pasku
bocznym (`brandIcon` w interfejsie) zostanie przerysowana z nowego SVG. Do czasu nowego logo obecne
zostaje wszędzie tam, gdzie jest.
