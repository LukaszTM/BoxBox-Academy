# BoxBox Academy – notatki wydania

## 0.7.0-beta (2.11.2026) – pierwsza paczka dla testerów

Paczka: `BoxBoxAcademy-0.7.0-beta.zip` (z klipami głosu) i `-bez-glosu.zip`. Wymagania: Windows, Python 3.12+, F1 25 (format UDP 2025 lub 2026).

### Trener

- Model zakrętów z wielu czystych okrążeń zamiast jednego okrążenia referencyjnego: odstające próby odrzucane (MAD), cel to ważona średnia najlepszych prób, starsze sesje ważą mniej. Najlepsze okrążenie zostaje drugim punktem odniesienia.
- Po okrążeniu: sektor z największą stratą („najwięcej tracisz w drugim sektorze, około pół sekundy”) i konkretne polecenie z liczbą („na następnym okrążeniu zacznij hamować wcześniej, o jakieś dwadzieścia metrów”).
- Trening względem najlepszych: w Time Trial z duchem z rankingu program zapamiętuje okrążenie najlepszych na torze (bez nazwiska). Potem w każdym trybie mówi, ile tracisz do najlepszych, w którym zakręcie i co oni robią inaczej; cel na dziś to połowa różnicy.
- Uczciwe porównanie: paliwo, mieszanka i zużycie opon, uszkodzenia, deszcz i asysty są brane pod uwagę. Strata jest rozbijana na warunki i jazdę; w deszczu i z uszkodzeniami porównanie jest wstrzymane.
- Prowadzenie w nieopanowanych zakrętach na żywo: „puść gaz”, „mocny hamulec”, „pół gazu”, „pełny gaz” przed punktem z referencji.
- Rady po okrążeniu o DRS, baterii i oponach; plan baterii na okrążenie; dziennik kontaktów w wyścigu z zasadą po sytuacji.
- Tor bez pliku zakrętów: zakręty wyznaczane z pierwszego pełnego okrążenia (np. Madryt z pakietu 2026).

### Okno

- Nowy Start (Racing Command Center): obrys toru z kropkami-bolidami, Pit Control, licencja.
- Zakładka Umiejętności: sześć wymiarów 0–100 z trendem i wskazówkami, raport PDF sesji.
- Postęp: spójność jazdy, odsetek czystych, „wtedy vs dziś”, sektory S1–S3, suma najlepszych sektorów.
- Analiza: wykresy DRS i baterii, strefy DRS na mapie, dowolne okrążenie sesji lub „najlepsi na świecie” jako referencja, eksport CSV z DRS i baterią.
- Lekcje: DRS w każdej strefie, bateria na prostych, opony w oknie (cele liczone z danych).
- HUD: moduł DRS · bateria · sektory; osiem modułów przeciąganych w edytorze.
- Karta kierowcy: zdjęcie jako zaokrąglony kwadrat z ręcznym dopasowaniem.
- Bez migania: strona podmienia tylko zmienione elementy; powiększenie także z wysokości ekranu.
- Lektor samouczka (klipy `tutorial_*`).

### Dla testerów

- `CZYTAJ-TO.txt` w paczce, PDF-y: co nagrać, formularze, antywirus/SmartScreen, dokumentacja, lista torów.
- Discord: https://discord.gg/t82VhVkVq
- Nowe klipy głosu do wygenerowania (`wygeneruj_glos.bat` generuje tylko brakujące): sektory, polecenia, mistrz, samouczek.

### Znane ograniczenia

- Współczynniki paliwa i opon są orientacyjne (reguły kciuka F1), do strojenia na danych testerów.
- Okrążenie najlepszych powstaje tylko w Time Trial z wybranym duchem z rankingu; bez tego trener porównuje do Twojej referencji.
- Ustawienia auta (pakiet Car Setup) nie są jeszcze czytane.
- Tylko F1 25 i 2026 Season Pack; F1 23/24 nie.

## 0.6.0-beta (28.10.2026)

Wersja wewnętrzna: hybryda GUI z makiety racing, analiza umiejętności, odznaki, raport PDF, auto-tor, prowadzenie w zakrętach.
