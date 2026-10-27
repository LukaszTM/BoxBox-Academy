# Makieta v2 – lista zmian i brief nowej nakładki

Stan: makieta v1 (27.10) jest już interfejsem programu. Poniższe punkty to poprawki do wykonania
w makiecie v2; po ocenie trafią do programu jako edycja HTML/CSS. Teksty podane kursywą są
docelowe.

## A. Poprawki w istniejących ekranach

1. **Czytelność z fotela.** Minimalne rozmiary: etykiety w kapitalikach 12 px, tekst pomocniczy 13 px, czas przy komunikacie 11 px, wartości w tabelach 13 px. Kolor tekstu pomocniczego #8d98a8 zamiast #657186. Nagłówki i duże liczby bez zmian.
2. **Hero na Starcie.** Hasło *„Każdy zakręt może być lepszy.”* tylko do pierwszej sesji. Po niej w tym miejscu karta akcji jest niższa: tryb, nazwa sesji, przełączniki, JEDŹ. Narysować oba stany.
3. **Lekcje.** Opis wybranej lekcji ma pole na cel z programu, np. *„Hamuj w T1 o 10 m wcześniej niż dziś, 3 razy z rzędu”* (kierunek i liczba przychodzą z silnika). Dla lekcji „jeden zakręt” pole wyboru zakrętu (lista numerów z toru).
4. **Etykiety premium w becie.** Usunąć „PIT CREW / PLANOWANE” z ekranów bety; zostaje tylko „wkrótce” przy trybie Wyścig i jedna karta „Co dalej po becie” w Pomocy.
5. **Ustawienia → Dane.** Pola: *Folder danych* (ścieżka obok programu) z przyciskiem *Otwórz folder*, *Folder nagrań*, przełącznik *Domyślnie nagrywaj sesje*, liczby: sesje i okrążenia w bazie, przycisk *Zapakuj raport błędu* z miejscem na wynik (ścieżka ZIP).
6. **Postęp → trend.** Podtytuł z nazwą toru (w v1 był błąd szablonu). Pod wykresem najlepsze czasy per krok asyst (lista 1–4 wierszy).

## B. Jeden wzór paska komunikatu (cały program)

Pasek w stronie, nad treścią, pod nagłówkiem. Trzy odmiany tego samego komponentu:

- **Błąd** (czerwona ramka 1 px, tło ciemnoczerwone, ikona ostrzeżenia): *„Port 20777 zajęty: zamknij inny program z telemetrią”*, *„Brak pliku toru dla tego toru: trener wyłączony, zapisuję tylko przebieg”*, *„Błąd w trenerze, szczegóły w dzienniku data/boxbox.log”*.
- **Informacja** (cyjanowa ramka): *„Gra wysyła telemetrię: trener wystartował sam”*, *„Sesja zakończona automatycznie: brak sygnału z gry od 20 s”*.
- **Sukces** (zielona ramka): *„Zapisano CSV: data/eksport/okrazenie-12.csv”*, *„Zdjęcie zapisane”*.

Każdy ma tekst, opcjonalny przycisk akcji po prawej (*Sprawdź telemetrię*, *Otwórz folder*) i krzyżyk. Informacja i sukces znikają same po 6 s, błąd zostaje do zamknięcia. Ten sam pasek zastępuje dzisiejsze „toasty” w rogu.

## C. Elementy brakujące

7. **Samouczek w dymkach.** Dymek przy elemencie (ramka czerwona 2 px, tło #2b1d1e, strzałka w stronę elementu, licznik *„Samouczek 2/7”*, przyciski *Dalej* i *Zamknij*). Narysować 3 pozycje: przy pastylce stanu, przy JEDŹ, przy plakietce. Kolejność kroków: Start, pastylka stanu, JEDŹ, panel na żywo, Karta kierowcy, Postęp, Ustawienia.
8. **Stany puste.** Analiza bez sesji, Postęp bez okrążeń, Start przed pierwszą sesją (bez „Ostatnia sesja”), Sesja na żywo przed pierwszym pełnym okrążeniem (wykres z tekstem *„Wykres pojawi się po pierwszym pełnym okrążeniu”*). Każdy stan: ikona, jedno zdanie, jeden przycisk.
9. **Kreator, krok Kierowca.** Nick, zdjęcie (siatka miniatur z folderów Obrazy i Pulpit, bez okna dialogowego), przełącznik zgody na anonimowe statystyki z jednym zdaniem.
10. **Mapa toru w Analizie** z prawdziwego kształtu: obrys toru, linia mety, numery zakrętów, czerwone punkty hamowania gracza, szare referencji, podświetlenie wybranego zakrętu, mały wskaźnik DRS na prostych. Jako wzorzec kształtu: zdjęcia torów od Ciebie (Bahrajn, Monza, Suzuka). Stan bez kształtu: *„Nagraj jedno okrążenie recorderem, a mapa pojawi się tutaj”*.
11. **Tabela przejazdów:** nazwy reguł po polsku w kolumnie Uwagi po najechaniu (tooltip w stronie), sortowanie po nagłówku, wiersz najlepszego okrążenia wyróżniony.

## D. Nowa nakładka na grę: HUD w stylu F1, nie okno

Zasada: nakładka nie ma tła ani ramki. To zestaw elementów graficznych w stylu grafik telewizyjnych
F1 (timing tower, pasek nazwiska, wstęgi z ukośnie ściętymi rogami), rozmieszczonych przy krawędziach
ekranu, tak żeby nie zasłaniać toru, lusterek ani HUD-u gry. Cała reszta ekranu jest przezroczysta
i klikalna dla gry.

Styl:

- Wstęgi z ukośnym ścięciem jednego rogu (jak paski F1 TV), cienka linia akcentu Signal Red lub
  Telemetry Cyan na krawędzi, bez zaokrągleń typu „karta”.
- Tło każdej wstęgi półprzezroczyste ciemne z suwakiem krycia 0–100 % (0 = sam tekst). Tekst ma
  cienki ciemny obrys lub poświatę, żeby był czytelny nawet przy kryciu 0 na jasnym niebie.
- Czcionka wąska, wyścigowa, kapitaliki w etykietach (np. Titillium Web / Exo 2 / Rajdhani); liczby w
  kroju tabelarycznym, żeby nie skakały.
- Kolory z palety programu; nic nie miga; zmiany przez krótkie przejścia (wjazd wstęgi 200 ms).
- Wszystko skalowalne 65–160 %, każdy blok z osobna można przesunąć myszą (pozycje zapamiętane),
  każdy blok można wyłączyć w ustawieniach.

Bloki (narysować każdy osobno i jedną kompozycję na zrzucie z gry 1920×1080):

1. **Zakręt** (góra, środek, pod HUD-em gry): wstęga z *T8–T10* w cyjanie 40 px i *za 120 m* 20 px;
   pod nią cienki pasek odległości malejący do zera; przy < 15 m napis *TERAZ*. To jedyny duży element.
2. **Cel na okrążenie** (pod blokiem zakrętu, mniejszy): żółta wstęga *POPRAW · T1–T2 · hamuj 20 m
   wcześniej*. Znika po przejechaniu tego zakrętu, wraca na kolejnym okrążeniu.
3. **Radio mechanika** (dół, lewo, nad lusterkiem/nad HUD-em): ostatni komunikat 16–18 px z ikoną
   radia i czasem; pojawia się na 8 s i zjeżdża; poprzednie dwa jako mniejsze linie nad nim (do
   wyłączenia).
4. **Delta i okrążenie** (góra, prawo, jak wieża czasów): *OKRĄŻENIE 4* i delta do referencji
   *−0,41 s* (zielona) / *+0,12 s* (bursztynowa), pod spodem mały pasek celu kroku *2/3 czystych*.
5. **Po okrążeniu** (na 6 s, środek dolnej części): wstęga z czasem okrążenia i deltą, pod nią
   *DOBRZE · …* (zielone) i *DO PRACY · …* (bursztynowe). Potem znika.
6. **Mini-mapa** (prawy dolny róg, 140×90 px, opcjonalna): obrys toru z recordera, punkt auta,
   znacznik następnego punktu hamowania, bez tła.
7. **Stan** (lewy górny róg, bardzo mały): *● TRENER · NAGRYWAM · 00:14:32*; w stanie „czekam na
   telemetrię” tylko ten blok z napisem *Czekam na grę · port 20777*.

Narysować: kompozycję na zrzucie z F1 25 (kokpit, trening), wersję z kryciem 0 % i 70 %, stan
„po okrążeniu”, stan „czekam”. Wysokość wszystkich bloków razem nie większa niż 25 % ekranu.

## E. Co dostarczyć

- Makieta v2 jako jeden plik HTML (jak v1) z ekranami A–C oraz osobną stroną nakładki HUD (D) na zrzucie z gry; każdy blok nakładki jako osobny element HTML z przezroczystym tłem, bo zostanie użyty 1:1 w programie.
- Zdjęcia kształtów torów: Bahrajn, Monza, Suzuka (zrzut mapy z gry lub z sieci), do odwzorowania obrysu i numeracji zakrętów.
