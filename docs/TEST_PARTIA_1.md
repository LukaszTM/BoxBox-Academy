# Test partii 1: trener z głosem, postęp, nakładka

Jedna paczka, jedno generowanie głosu, dwie sesje po 5–6 okrążeń. Wszystko, co zauważysz,
zapisz w `recordings\<plik>.txt` albo w tej liście (skopiuj do notatek i odhaczaj).

## Przed grą (raz)

1. Rozpakuj paczkę do **nowego, pustego** folderu (np. `C:\boxbox-partia1`). Zamknij stare terminale.
2. Paczka ma już 93 gotowe klipy z poprzedniej tury (`assets\voice`); generator je pominie.
3. `wygeneruj_glos.bat`: podaj klucz API i ID głosu (`gFl0NeqphJUaoBLtWrqM`, Piotr). Skrypt pokaże
   liczbę brakujących klipów i znaków (ok. 600 klipów, ok. 40 tys. znaków, plan Creator ma 100 tys.).
   Wpisz `t`. Trwa ok. 10–15 minut. Na końcu sam nakłada efekt radia.
4. `glos-test.bat`: słychać powitanie i przykładowy komunikat? Głośność w porządku na tle gry?
   Jeśli za cicho, w `trener.bat` zmień `VOLUME=1.5` na `2.0`.
5. `spakuj.bat assets\voice\raw` → `raw.tar.xz.part001`, `part002`… (po 20 MB). Prześlij wszystkie części na GitHub (folder `recordings`).

## Sesja 1: Monza, trening, TC średnia, ABS wł. (5–6 okrążeń)

Gra: tryb okna bez ramki, telemetria UDP 20777, format 2025 lub 2026.

1. `trener.bat monza partia1` – w terminalu powinno być: liczba klipów, powitanie od razu.
2. Nakładka pojawia się w lewym górnym rogu (przeciągnij ją tam, gdzie nie zasłania lusterek).
3. Jedź: okrążenie wyjazdowe, potem 2 czyste, potem 2 z celowymi błędami (T1 późne hamowanie,
   Lesmo gaz za wcześnie, Ascari hamulec puszczony naraz), potem 1 czyste.
4. Esc na nakładce (albo Ctrl+C). Terminal wypisze tabelę, postęp i „Obciążenie: X%”.

Sprawdź i zapisz:

- [ ] Powitanie „Mechanik na radiu…” słychać zaraz po starcie (przed wyjazdem).
- [ ] Po pierwszym pełnym okrążeniu: „Mam twoje najlepsze okrążenie…” albo „Pierwsze okrążenie zapisane…”.
- [ ] Komunikat po zakręcie przychodzi w ciągu ok. 2 s od wyjścia z zakrętu (nie w następnym zakręcie).
- [ ] To, co mówi mechanik, zgadza się z linią „Mechanik:” w terminalu i z napisem na nakładce.
- [ ] Celowe błędy zostały wyłapane (T1 późne hamowanie, Lesmo gaz, Ascari hamulec).
- [ ] Po czystym okrążeniu: „Czyste okrążenie, pierwsze z trzech” / „drugie z trzech”.
- [ ] Po 3 czystych z rzędu (jeśli się uda): komunikat o kolejnym kroku (TC wyłączona).
- [ ] Nakładka: numer okrążenia, zbliżający się zakręt z metrami, ostatnie 3 komunikaty czytelne z fotela.
- [ ] Głośność: mechanik słyszalny na tle silnika, nie przesterowany.
- [ ] Linia „Obciążenie:” po zakończeniu – zapisz wartość (cel: poniżej 10% jednego rdzenia).
- [ ] Gra nie gubiła klatek z nakładką (jeśli tak, zapisz; spróbuj `SKALA=0.8` albo `NAKLADKA=0`).

## Sesja 2: Suzuka, Time Trial, TC wyłączona, ABS wł. (5–6 okrążeń)

1. `trener.bat suzuka partia1`
2. Jedź 5–6 okrążeń normalnie, bez celowych błędów. Pozwól sobie na naturalne błędy.
3. Esc / Ctrl+C.

Sprawdź i zapisz:

- [ ] Bez TC trener częściej mówi o gazie na wyjściu / trakcji (ma większą wagę).
- [ ] Po okrążeniu bez asysty ERS (Time Trial ma ją wyłączoną): rada o baterii, jeśli jest co radzić.
- [ ] Nakładka pokazuje „krok 3: TC wyłączona, czyste z rzędu N/3”.
- [ ] Po sesji `postep.bat`: Monza i Suzuka, krok, najlepsze czasy, zakręty opanowane / do pracy.
- [ ] Zapisz, które komunikaty były zbędne albo zbyt częste, i które zabrakły.

## Po testach prześlij

- `recordings\*.bin.xz` (po `spakuj.bat`) + `.txt` z notatkami,
- `data\boxbox.sqlite`,
- części `raw.tar.xz.part…` z `spakuj.bat assets\voice\raw`,
- ten plik z odhaczonymi punktami albo zdjęcie/zrzut nakładki, jeśli coś było nieczytelne.
