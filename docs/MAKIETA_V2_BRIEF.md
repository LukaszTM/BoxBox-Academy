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

## D. Nowa nakładka na grę (osobne okno nad grą)

Wymagania:

- Okno 600 × ok. 420 px (skala 65–160 %), bez ramki systemowej, przeciągane, krycie 40–100 %, zawsze na wierzchu. Tło ciemne jak panel ze szkła, ale bez rozmycia (nad grą rozmycie nie działa); ramka 2 px Signal Red.
- Musi być czytelne z fotela przy skali 100 %: zakręt 40 px, metry 20 px, komunikat 16–18 px.
- Bez przycisków i pól; zamyka się z okna programu albo Esc.
- Narysować trzy stany: **czekam na telemetrię**, **jazda** (pełna treść), **po okrążeniu** (przez 6 s większe „Dobrze / Do pracy” zamiast listy komunikatów).

Treść stanu „jazda”, od góry:

1. Pasek: *BOXBOX ACADEMY* po lewej, *OKRĄŻENIE 4* na środku, po prawej *● NAGRYWAM* (zielone) lub *● TRENER* i czas sesji.
2. Zakręt: *T8–T10* w cyjanie, obok *za 120 m*; gdy do apeksu mniej niż 15 m: *TERAZ*. Pod spodem cienki pasek odległości (maleje do zera).
3. Żółta linia celu na okrążenie: *Popraw: T1–T2, hamuj 20 m wcześniej*.
4. Trzy ostatnie komunikaty mechanika z czasem, najnowszy większy i jaśniejszy.
5. Cel kroku z paskiem: *3 czyste okrążenia z rzędu · 2/3*.
6. Dolny pasek w monospace: *245 km/h · bieg 6 · 3 481 m* po lewej, delta do referencji po prawej (*−0,41 s* na zielono, *+0,12 s* na bursztynowo).
7. Mała mapa toru w prawym górnym rogu (kształt z recordera, punkt auta, znacznik następnego punktu hamowania), 120 × 80 px, do wyłączenia w ustawieniach.

Stan „po okrążeniu”: duży czas okrążenia z deltą, pod nim *Dobrze: …* (zielone) i *Do pracy: …* (bursztynowe), po 6 s powrót do stanu „jazda”.

Stan „czekam”: logo, *Czekam na telemetrię z gry*, port.

## E. Co dostarczyć

- Makieta v2 jako jeden plik HTML (jak v1) z ekranami A–C oraz osobnym widokiem nakładki w trzech stanach (D).
- Zdjęcia kształtów torów: Bahrajn, Monza, Suzuka (zrzut mapy z gry lub z sieci), do odwzorowania obrysu i numeracji zakrętów.
