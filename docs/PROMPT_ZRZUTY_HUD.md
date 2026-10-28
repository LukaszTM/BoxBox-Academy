# Zrzuty z gry jako tła edytora HUD: prompt do podmiany logo

Cel: zrzuty z F1 25 (kokpit, kamera T, maska, widok z tyłu) mają trafić do programu jako tła w zakładce
HUD F1, żeby gracz ustawiał moduły na prawdziwym widoku z gry. Do programu nie mogą wejść cudze znaki
towarowe ani dane osobowe: logo F1, nazwy sponsorów, nazwa zespołu, malowanie zespołu, nazwy graczy z
wieży czasów. Geometria kadru (halo, lusterka, deska, ramki HUD gry) musi zostać bez zmian, bo o nią chodzi.

## Co dać ChatGPT

Jeden zrzut na raz, w pełnej rozdzielczości (2560×1440). Do każdego ten sam prompt. Wynik ma być w tej
samej rozdzielczości, bez kadrowania.

## Prompt (angielski, działa najlepiej z modelami obrazu)

```
Edit this racing game screenshot. Keep the exact framing, camera, car geometry, halo, mirrors,
steering wheel, track, grandstands and every HUD panel in the same place and size. Change only
the branding and names:

1. Replace every sponsor logo and brand name on the car, halo, mirrors, steering wheel, suit,
   gloves, trackside boards and bridges with fictional ones: "VELOX", "NORDWIND", "ORBITAL",
   "KESTREL", "PANTHEON". Use the same font weight, size, colour and placement as the originals.
2. Change the team livery colours to a generic scheme: dark graphite with white and electric-blue
   accents. No real team colours, no real team logos, no star emblems.
3. In the top-left timing panel replace the "F1" emblem and the mode label with the text
   "TIME TRIAL" in a plain sans-serif, and replace all driver names with "DRIVER 1", "DRIVER 2",
   "DRIVER 3". Keep the panel shape, background and the lap times.
4. In the top-right sector panel keep the layout and numbers, remove any logos.
5. Trackside advertising: replace tyre brand boards and airline boards with the fictional names
   above, same colours and sizes.
6. Do not add new objects, text, watermarks or effects. Do not change lighting, resolution or
   aspect ratio. Output the full image at the original resolution.
```

## Prompt (polski, gdy ChatGPT lepiej reaguje na polski)

```
Zedytuj ten zrzut z gry wyścigowej. Zachowaj dokładnie kadr, kamerę, geometrię bolidu, halo, lusterka,
kierownicę, tor, trybuny i każdy panel HUD w tym samym miejscu i rozmiarze. Zmień wyłącznie marki i nazwy:
1. Każde logo sponsora i nazwę marki na bolidzie, halo, lusterkach, kierownicy, kombinezonie,
   rękawicach, bandach i mostach zamień na fikcyjne: „VELOX”, „NORDWIND”, „ORBITAL”, „KESTREL”,
   „PANTHEON”. Ta sama grubość, wielkość, kolor i miejsce napisu co w oryginale.
2. Malowanie zespołu zamień na neutralne: ciemny grafit z białymi i elektrycznie niebieskimi akcentami.
   Bez barw i logo prawdziwych zespołów, bez emblematów z gwiazdą.
3. W panelu czasów w lewym górnym rogu zamień emblemat „F1” i etykietę trybu na napis „TIME TRIAL”
   zwykłym bezszeryfowym krojem, a wszystkie nazwy kierowców na „DRIVER 1”, „DRIVER 2”, „DRIVER 3”.
   Kształt panelu, tło i czasy zostają.
4. W panelu sektorów w prawym górnym rogu zachowaj układ i liczby, usuń wszelkie loga.
5. Reklamy przy torze: bandy producenta opon i linii lotniczych zamień na fikcyjne nazwy jak wyżej,
   w tych samych kolorach i rozmiarach.
6. Nie dodawaj obiektów, tekstów, znaków wodnych ani efektów. Nie zmieniaj oświetlenia, rozdzielczości
   ani proporcji. Zwróć pełny obraz w oryginalnej rozdzielczości.
```

## Po otrzymaniu obrazów

1. Sprawdź na każdym: brak „F1”, brak nazwy opon, linii lotniczych i zespołu, brak nicków w wieży czasów,
   halo i lusterka na swoim miejscu (porównaj z oryginałem nakładając jeden na drugi w podglądzie).
2. Nazwij pliki: `tlo-kokpit.jpg`, `tlo-kamera-t.jpg`, `tlo-maska.jpg`, `tlo-tyl.jpg` (JPG, jakość 85,
   2560×1440; rozmiar ok. 400–700 KB każdy).
3. Wyślij tutaj; trafią do `boxbox/gui/web/tla/` i do listy „Tło” w zakładce HUD F1 w programie.

## Uwaga prawna, w jednym zdaniu

Podmiana logo usuwa znaki towarowe i dane osobowe, ale sam obraz nadal jest renderem z gry EA. Jako tło
w edytorze (nie w materiałach promocyjnych) ryzyko jest małe; do publikacji i sklepu używamy wyłącznie
własnych ilustracji albo zrzutów z nakładką na własnym nagraniu wideo.
