# Lista torów: F1 25 i sezon 2026

Źródło identyfikatorów: specyfikacja telemetrii EA (F1 25 v3 i 2026 Season Pack, Season 8).
Długości orientacyjne (km); program bierze dokładną długość z pakietu Session gry.
Kolumna „Stan w programie”: plik toru = zakręty do trenera (`boxbox/tracks/data/<id>.json`),
kształt = obrys z recordera do mapy (`boxbox/tracks/shape/<id>.json`).

## Tory kalendarza (potrzebne do bety)

| ID | Tor | Kraj | Długość | F1 25 (sezon 2025) | Sezon 2026 | Stan w programie |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | Melbourne (Albert Park) | Australia | 5,28 | tak | tak | brak |
| 2 | Shanghai | Chiny | 5,45 | tak | tak | brak |
| 13 | Suzuka | Japonia | 5,81 | tak | tak | plik toru: tak, kształt: brak |
| 3 | Sakhir (Bahrajn) | Bahrajn | 5,41 | tak | tak | plik toru: tak, kształt: brak |
| 29 | Jeddah | Arabia Saudyjska | 6,17 | tak | tak | brak |
| 30 | Miami | USA | 5,41 | tak | tak | brak |
| 27 | Imola | Włochy | 4,91 | tak | nie (poza kalendarzem 2026) | brak |
| 5 | Monaco | Monako | 3,34 | tak | tak | brak |
| 4 | Catalunya (Barcelona) | Hiszpania | 4,66 | tak | tak | brak |
| 6 | Montreal | Kanada | 4,36 | tak | tak | brak |
| 17 | Austria (Red Bull Ring) | Austria | 4,32 | tak | tak | brak |
| 7 | Silverstone | Wielka Brytania | 5,89 | tak | tak | brak |
| 10 | Spa-Francorchamps | Belgia | 7,00 | tak | tak | brak |
| 9 | Hungaroring | Węgry | 4,38 | tak | tak | brak |
| 26 | Zandvoort | Holandia | 4,26 | tak | tak | brak |
| 11 | Monza | Włochy | 5,79 | tak | tak | plik toru: tak, kształt: brak |
| 42 | Madrid (Madring) | Hiszpania | 5,47 | nie (tylko 2026 Season Pack) | tak | obrys z atlasu: tak |
| 20 | Baku | Azerbejdżan | 6,00 | tak | tak | brak |
| 12 | Singapore (Marina Bay) | Singapur | 4,94 | tak | tak | brak |
| 15 | Texas (COTA, Austin) | USA | 5,51 | tak | tak | brak |
| 19 | Mexico (Hermanos Rodríguez) | Meksyk | 4,30 | tak | tak | brak |
| 16 | Brazil (Interlagos) | Brazylia | 4,31 | tak | tak | brak |
| 31 | Las Vegas | USA | 6,20 | tak | tak | brak |
| 32 | Losail (Katar) | Katar | 5,42 | tak | tak | brak |
| 14 | Abu Dhabi (Yas Marina) | ZEA | 5,28 | tak | tak | brak |

Razem: 25 torów kalendarza (24 w F1 25, 24 w sezonie 2026; Imola tylko 2025, Madrid tylko 2026).

## Tory dodatkowe w grze (poza kalendarzem, niższy priorytet)

| ID | Tor | Uwagi |
| --- | --- | --- |
| 39 | Silverstone (Reverse) | układ odwrócony, tylko F1 25 |
| 40 | Austria (Reverse) | układ odwrócony, tylko F1 25 |
| 41 | Zandvoort (Reverse) | układ odwrócony, tylko F1 25 |

## Co jest potrzebne dla każdego toru

1. **Nagranie recorderem** (`recorder.bat`): co najmniej 2 pełne okrążenia z pakietem Motion. Daje kształt toru do mapy i surowe dane.
2. **Plik toru** z zakrętami: z nagrania poleceniem `python -m boxbox.tracks.detect <nagranie> --car pb`, potem nazwy zakrętów jak w grze (T1, T4–T5…). Trzy tory są gotowe: Bahrajn, Monza, Suzuka.
3. **Przewodnik** (`guide/<id>.json`): apeksy z notatkami do nakładki; powstaje z pliku toru.
4. **Zdjęcie/mapa toru** jako wzorzec numeracji zakrętów i do sprawdzenia obrysu.

Jedno nagranie recorderem (ok. 5 minut jazdy na tor) wystarczy na punkty 1–3. Dla 22 brakujących torów to ok. 2–3 godziny jazdy w Time Trial.

## Kolejność proponowana

1. Tory z gotowymi plikami: Bahrajn, Monza, Suzuka (brakuje tylko kształtów).
2. Najczęściej jeżdżone przez początkujących i proste do nauki: Austria, Catalunya, Silverstone, Spa, Zandvoort, Melbourne.
3. Reszta kalendarza 2025.
4. Madrid po premierze 2026 Season Pack (ID 42; program już zna ten identyfikator).
5. Układy odwrócone: tylko jeśli zostanie czas.
