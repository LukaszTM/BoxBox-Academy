# BoxBox Academy – serwer Discord dla testerów: konfiguracja krok po kroku

Zaproszenie: https://discord.gg/t82VhVkVq

Cel serwera: zamknięte testy bety. Ma być prosty: pięć kanałów tekstowych, jeden głosowy, dwie role.
Konfiguracja zajmuje około 20 minut. Wszystko robisz w aplikacji Discord na komputerze.

## 1. Ustawienia serwera

1. Kliknij nazwę serwera (lewy górny róg) → **Ustawienia serwera**.
2. **Przegląd:** wgraj logo z `assets/` (plik `logo_small.png` z `dist/` po zbudowaniu PDF-ów albo logo z repo).
3. **Bezpieczeństwo → Poziom weryfikacji:** „Średni” (konto starsze niż 5 minut). Blokuje najprostsze boty, nie blokuje ludzi.
4. **Bezpieczeństwo → Filtr treści:** „Skanuj wiadomości od wszystkich”.
5. **Zaproszenia:** jeśli chcesz kontrolować liczbę testerów, zrób nowe zaproszenie z limitem użyć (np. 25) zamiast bezterminowego.
6. **Społeczność:** na razie nie włączaj. Serwer społecznościowy wymaga regulaminu, kanału zasad i bywa widoczny szerzej.

## 2. Role

**Ustawienia serwera → Role → Utwórz rolę.** Dwie wystarczą.

| Rola | Kolor | Uprawnienia | Kto |
| --- | --- | --- | --- |
| Autor | czerwony | Administrator | tylko Ty |
| Tester | cyjan | domyślne + „Załączaj pliki”, „Osadzaj linki”, „Dodawaj reakcje” | każdy zaproszony |

Rolę Tester nadajesz ręcznie po wejściu osoby (klik na nick → Role). Dzięki temu ktoś z przypadkowego linku
nie widzi kanałów testowych: w kroku 3 ustawiasz, że kanały widzi tylko Tester.

Rola `@everyone`: w **Role → @everyone → Uprawnienia** wyłącz „Wysyłaj wiadomości” i „Załączaj pliki”.
Nowa osoba bez roli zobaczy tylko `#start` i nic nie napisze, dopóki nie dostanie roli.

## 3. Kategorie i kanały

Prawy klik na liście kanałów → **Utwórz kategorię**, potem w kategorii **Utwórz kanał**.

Kategoria **INFO**

| Kanał | Typ | Uprawnienia | Po co |
| --- | --- | --- | --- |
| #ogłoszenia | tekstowy | pisze tylko Autor, czytają wszyscy | nowe wersje, co się zmieniło, link do paczki |
| #start | tekstowy | pisze tylko Autor, widzą wszyscy | przypięta instrukcja startu (tekst w p. 5) |

Kategoria **TESTY** (widoczna tylko dla roli Tester: w ustawieniach kategorii → Uprawnienia → @everyone: „Wyświetl kanał” wyłączone; Tester: włączone)

| Kanał | Typ | Ustawienia | Po co |
| --- | --- | --- | --- |
| #zgłoszenia | forum | wymagane tagi: błąd, pytanie, działa; szablon w p. 5 jako wytyczne postów | jedno zgłoszenie = jeden wątek |
| #nagrania | forum | tagi: Monza, wyścig, Madryt, inny tor | jedna sesja = jeden wątek z plikami |
| #pomysły | tekstowy | tryb wolny (slowmode) 30 s | propozycje, bez błędów |
| #off-topic | tekstowy | bez ograniczeń | reszta |
| Sesja na żywo | głosowy | limit 10 osób | wspólna jazda, słuchanie mechanika |

Kanały typu **forum** są lepsze od zwykłych na zgłoszenia i nagrania: każdy temat ma własny wątek i tagi,
nic nie ginie w strumieniu. Przy tworzeniu kanału wybierz „Forum” zamiast „Tekstowy”.

## 4. Limity plików

Discord bez Nitro przyjmuje pliki do 10 MB (serwer bez poziomów boostów). Nagrania po `spakuj.bat`
mają części po 20 MB, więc na Discord będą za duże. Dwie opcje:

1. Nagrania nadal wysyłane na GitHub (jak dotąd), a na Discord tylko formularz i zrzut podsumowania. Prostsze dla Ciebie.
2. Zmiana dzielenia na części po 9 MB w `spakuj.bat` (parametr rozmiaru części). Więcej plików, ale wszystko w jednym miejscu.

Rekomendacja na start: opcja 1. W `#nagrania` tester wkleja formularz i zrzut, a plik nagrania wysyła przez
GitHub albo dowolny dysk w chmurze z linkiem w wątku.

## 5. Teksty do przypięcia

Po wklejeniu wiadomości: prawy klik → **Przypnij wiadomość**.

### #start

```
Cześć, to zamknięte testy BoxBox Academy, trenera jazdy do F1 25. Program czyta telemetrię gry
na Twoim komputerze i mówi głosem mechanika, co poprawić. Nic nie wysyła do sieci.

Jak zacząć:
1. Pobierz paczkę z #ogłoszenia i rozpakuj. Potrzebny Python 3.12 lub nowszy (python.org, zaznacz "Add to PATH").
2. Uruchom akademia.bat. Gdy Windows ostrzega, zobacz PDF o antywirusie w folderze docs.
3. W grze włącz telemetrię UDP: port 20777, adres 127.0.0.1, format 2025 albo 2026.
   Dla nakładki HUD gra w oknie bez ramki.
4. Przejdź kreator, kliknij JEDŹ i jedź trening. Pierwsze okrążenie to odniesienie, od drugiego mechanik mówi.

Po sesji: błędy do #zgłoszenia (szablon w wytycznych kanału), nagrania i formularze do #nagrania,
pomysły do #pomysły. Obsługiwane są tylko F1 25 i 2026 Season Pack. Wersja programu jest w lewym
dolnym rogu okna, podawaj ją w każdym zgłoszeniu.
```

### #zgłoszenia (wytyczne postów w ustawieniach kanału forum)

```
Wersja (lewy dolny róg okna):
Tor, tryb w grze, format UDP (2025/2026):
Co zrobiłem:
Co się stało:
Czego się spodziewałem:
Zrzut ekranu albo film:
Plik z "Pomoc i wsparcie -> Raport błędu" (ZIP), jeśli program nie działa:
```

### #nagrania (wytyczne postów)

```
Jeden wątek na jedną sesję. W wątku: wypełniony formularz z docs/formularze, zrzut Podsumowania sesji,
link do nagrania (.bin.xz po spakuj.bat) albo informacja, że poszło na GitHub.
Nagrania zawierają tylko telemetrię gry, bez Twoich danych.
```

### #ogłoszenia (pierwszy wpis)

```
Paczka testowa 0.6.0-beta: [link do ZIP]
W środku: program, instrukcja startu (CZYTAJ-TO.txt), PDF-y w docs (co nagrać, formularze, antywirus).
Zmiany względem postu na Facebooku: model zakrętów z wielu okrążeń zamiast jednego referencyjnego,
komunikat o sektorze z największą stratą i konkretne polecenie na następne okrążenie.
```

## 6. Po konfiguracji

1. Wyślij zaproszenie czterem osobom z komentarzy (Kuba Mikołajczyk, Michał Grela, Sergiusz Stańko, Tomasz Krystianowski) i nadaj im rolę Tester.
2. Wrzuć paczkę ZIP do `#ogłoszenia`. Plik ma 112 MB, więc trafi tam jako link (GitHub Releases albo dysk w chmurze), nie jako załącznik.
3. Sam przejdź ścieżkę testera na czystym koncie Discord: czy bez roli widzisz tylko `#start`, czy po roli widzisz TESTY.

Czego nie robić: nie wklejaj na serwer klucza API, ścieżek z własnym nazwiskiem ani zrzutów z karty kierowcy z prawdziwym zdjęciem, jeśli nie chcesz, żeby zostały na stałe u testerów.
