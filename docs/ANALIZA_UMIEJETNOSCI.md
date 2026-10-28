# Zakładka „Analiza umiejętności”: wytyczne

Dokument dla makiety i do wdrożenia w oknie. Silnik (`boxbox/coach/skills.py`) jest gotowy i przetestowany na nagraniach; zakładka ma tylko pokazać jego wynik tak, żeby początkujący wiedział, gdzie jest i co zrobić, żeby liczba rosła. Podgląd z konsoli: `python -m boxbox.app --skills`.

## 1. Cel zakładki w jednym zdaniu

Gracz po każdej sesji widzi sześć liczb 0–100, strzałkę trendu przy każdej i jedno zdanie, co zrobić, żeby liczba wzrosła. Nie ranking, nie ocena: mapa pracy.

## 2. Sześć wymiarów

| Wymiar | Co mierzy | Względem czego | Co podnosi wynik (przykład zdania) |
|---|---|---|---|
| Hamowanie | odchylenie punktu hamowania w każdym zakręcie: 0 m = 100, 80 m i więcej = 0; zakręt z obrotem = 0 | własne najlepsze okrążenie (albo duch z Time Trial, gdy jest w nagraniu) | „hamuj ok. 20 m później w T4” |
| Praca hamulcem | siła hamowania (różnica maksymalnego nacisku) i stopniowe puszczanie tam, gdzie referencja puszcza stopniowo | jak wyżej | „zwalniaj hamulec stopniowo aż do apeksu w T1–T2” |
| Gaz na wyjściu | odchylenie punktu pełnego gazu: 0 m = 100, 120 m = 0; zakręt z utratą przyczepności = 0 | jak wyżej | „łagodniej z gazem na wyjściu z T8–T10, tam tracisz przyczepność” |
| Powtarzalność | po połowie: rozrzut czasów (średnia do najlepszego: 0,5 % = 100, 3 % = 0) i odsetek czystych okrążeń | progi stałe, bez referencji | „3 z 5 okrążeń czystych; największe błędy w T1–T2” |
| Tempo | strata średniej z czystych okrążeń do referencji: 0 % = 100, 5 % = 0 | własne najlepsze albo duch | „najwięcej czasu tracisz w T6: 0,4 s na okrążenie” |
| Samodzielność | krok zdejmowania asyst (1–4 = 0, 25, 50, 75) plus do 25 pkt za serię czystych okrążeń na kroku | ścieżka asyst z etapu 5 | „2 czyste okrążenia do kroku: ABS wyłączony” |

Zasady wspólne:

- **Okno:** liczymy z ostatnich 10 ważnych okrążeń (pełne, bez pit lane, bez wyjazdu poza tor). Starsze okrążenia nie ciągną wyniku w dół ani w górę.
- **Minimum:** poniżej 5 okrążeń wymiar pokazuje „za mało danych”, nie liczbę. Wyjątek: samodzielność, bo krok asyst znamy od pierwszego okrążenia.
- **Trend:** różnica do profilu z poprzednich 10 okrążeń (np. +12). Bez poprzednich 10 okrążeń trendu nie ma i nie pokazujemy kreski ani zera.
- **Referencja:** technika (hamowanie, praca hamulcem, gaz) i tempo są liczone względem własnego najlepszego okrążenia. To ważne dla uczciwości: 90 w hamowaniu znaczy „powtarzasz swoje najlepsze”, nie „hamujesz jak zawodowiec”. Gdy w nagraniu jest duch z Time Trial, referencją jest duch i etykieta pod wymiarem to mówi. Powtarzalność ma progi stałe, więc jest porównywalna między graczami.
- **Bez łącznego „ratingu”** w becie. Jedna liczba zachęca do porównywania się z innymi i zniechęca początkujących; sześć liczb z zadaniami uczy. Jeśli kiedyś dojdzie ranking, będzie osobną decyzją.

## 3. Układ zakładki (do makiety)

Zakładka „Umiejętności” obok „Postęp” w pasku bocznym; ten sam szklany styl co reszta okna.

1. **Nagłówek:** wybór toru pastylkami (aktywny z czerwonym paskiem) plus pastylka „Wszystkie tory”. Pod spodem jedna linia: „10 ostatnich okrążeń, referencja: twoje najlepsze 1:26,918 (26.10)”.
2. **Wykres radarowy** po lewej: sześć osi, wypełnienie cyjanowe z kryciem 30 %, obrys cyjanowy; poprzednie okno jako szary cienki obrys, żeby trend było widać bez czytania liczb. Przy każdej osi nazwa wymiaru i liczba. Wymiar „za mało danych” rysowany szarym punktem w środku z etykietą „—”.
3. **Sześć kart** po prawej (dwie kolumny po trzy). Karta zawiera: nazwę wymiaru i liczbę dużym krojem (Barlow Condensed); strzałkę trendu z wartością („▲ +12”, „▼ −5”, brak przy braku trendu) w zieleni albo bursztynie; cienki pasek 0–100 pod liczbą; jedno zdanie „co podnosi wynik” (z silnika, jak w tabeli wyżej); etykietę małym krojem „względem: twoje najlepsze” albo „względem: duch Time Trial”. Kliknięcie karty otwiera Analizę z wykresem okrążenia przewiniętym do wskazanego zakrętu.
4. **Pasek dolny:** „Zadanie na następną sesję: …” z najsłabszego wymiaru (najniższa liczba; przy remisie ten z ujemnym trendem) i przycisk „Zacznij lekcję”, który otwiera lekcję pasującą do wymiaru: hamowanie → „Hamowanie w jednym zakręcie”, praca hamulcem → „Trail-braking”, gaz → „Gaz na wyjściu”, powtarzalność → „Czyste okrążenie”.
5. **Stan „za mało danych”** dla całej zakładki (mniej niż 5 okrążeń na torze): zamiast radaru ilustracja z napisem „Przejedź jeszcze N okrążeń na tym torze, a zobaczysz swój profil” i przycisk „Jedź”. Żadnych zer.
6. **Karta kierowcy:** mały radar (bez liczb) z profilu „Wszystkie tory” obok zdjęcia; kliknięcie prowadzi do zakładki.
7. **Raport PDF sesji** (etap 7): ten sam radar i sześć linii „wymiar: liczba, trend, zdanie”.

## 4. Czego nie robić

- Nie pokazywać liczby, gdy jest za mało danych, i nie uzupełniać zerami.
- Nie łączyć wymiarów w jedną ocenę i nie nazywać tego „rating” ani „ELO”.
- Nie porównywać z innymi graczami w becie (brak kont, brak zgody na dane).
- Nie zmieniać progów w oknie; progi są w silniku i w tym dokumencie, żeby liczby znaczyły to samo u każdego.
- Nie używać czerwieni dla niskiego wyniku; niski wynik to zadanie, nie błąd. Czerwień zostaje dla błędów programu i ostrzeżeń.

## 5. Dane i wydajność

- Wszystko liczy się z bazy (`laps`, `corner_metrics`, `lap_messages`, `progress`); żadnych nowych tabel.
- Profil liczymy po zakończeniu sesji i przy wejściu w zakładkę; dla 10 okrążeń to ułamek sekundy.
- `SkillProfile.to_dict()` daje gotowy słownik dla `app.js` (klucz, nazwa, podstawa, wynik, trend, zdanie, liczba okrążeń); profil łączny ma `trackId: null`.

## 6. Test odbioru

1. Nagranie Monzy z celowym błędem (okrążenie 4): hamowanie i powtarzalność niższe niż z samych czystych okrążeń, zdanie przy powtarzalności wskazuje T1–T2 (test `tests/test_skills.py`).
2. Nowy tor po trzech okrążeniach: zakładka pokazuje stan „za mało danych”, bez liczb.
3. Po 20 okrążeniach na torze każda karta ma trend.
4. Kliknięcie karty „Hamowanie” otwiera Analizę na wskazanym zakręcie.
5. Zdanie „co podnosi wynik” zgadza się z uwagami trenera z ostatniej sesji (ten sam zakręt).
