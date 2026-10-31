# BoxBox Academy – serwer Discord: struktura, role, boty i treści

Zaproszenie: https://discord.gg/t82VhVkVq

Serwer ma jeden cel na teraz: zamknięte testy bety z grupą 10–30 osób. Druga faza (publiczna beta) jest opisana na końcu, żeby nie przebudowywać serwera po drodze. Wszystkie teksty do wklejenia są w części 6.

## 1. Zasady, które porządkują wszystko

1. Jedno miejsce na jedną rzecz: błędy tylko w `#zgłoszenia`, nagrania tylko w `#nagrania`, pomysły tylko w `#pomysły`. Dyskusja ogólna w `#off-topic`.
2. Jedno zgłoszenie = jeden wątek. Kanały zgłoszeń i nagrań są forami, więc każdy temat ma własny wątek i tagi.
3. Nowa osoba bez roli widzi tylko `#start`, `#ogłoszenia` i `#przedstaw-się`. Resztę odblokowuje rola Tester, nadawana ręcznie.
4. Nic prywatnego na serwerze: bez kluczy API, bez ścieżek z nazwiskiem w zrzutach, bez nagrań z nazwami graczy (program anonimizuje nagrania sam).
5. Ty piszesz w `#ogłoszenia`, reszta tylko czyta i reaguje.

## 2. Struktura kanałów

Kolejność na liście jest celowa: od góry to, co nowa osoba ma zobaczyć najpierw.

| Kategoria | Kanał | Typ | Kto widzi | Kto pisze | Po co |
| --- | --- | --- | --- | --- | --- |
| (bez kategorii) | #start | tekstowy | wszyscy | tylko Autor | przypięte powitanie i instrukcja startu |
| INFO | #ogłoszenia | ogłoszeniowy | wszyscy | tylko Autor | nowe wersje, link do paczki, co się zmieniło |
| INFO | #przedstaw-się | tekstowy | wszyscy | wszyscy | jedna wiadomość od nowej osoby: na czym jeździ, jaki poziom; po niej rola Tester |
| INFO | #faq | tekstowy | wszyscy | tylko Autor | pytania, które padły więcej niż raz, z odpowiedziami |
| TESTY | #zgłoszenia | forum | Tester | Tester | błędy i problemy, jeden wątek na zgłoszenie, tagi: błąd, pytanie, działa, naprawione |
| TESTY | #nagrania | forum | Tester | Tester | jedna sesja = jeden wątek: formularz, zrzut, link do nagrania; tagi: Monza, Bahrajn, Suzuka, Madryt, inny tor, wyścig |
| TESTY | #pomysły | forum | Tester | Tester | propozycje funkcji, jeden wątek na pomysł; tagi: trener, okno, HUD, głos, inne |
| TESTY | #wersje-testowe | tekstowy | Tester | tylko Autor | paczki przed ogłoszeniem, do szybkiego sprawdzenia przez 2–3 osoby |
| SPOŁECZNOŚĆ | #off-topic | tekstowy | Tester | Tester | reszta: wyniki, memy, sprzęt |
| SPOŁECZNOŚĆ | #zrzuty-i-klipy | tekstowy | Tester | Tester | zrzuty z programu i filmy z jazdy z mechanikiem |
| SPOŁECZNOŚĆ | Sesja na żywo | głosowy | Tester | Tester | wspólna jazda, słuchanie komunikatów, limit 10 osób |
| ZAPLECZE | #dziennik-zmian | tekstowy | Tester | webhook GitHub | automatyczne wpisy o commitach i wydaniach (część 4) |
| ZAPLECZE | #autor-notatki | tekstowy | tylko Autor | tylko Autor | Twoje notatki z testów, lista do zrobienia |

Na start możesz pominąć `#faq`, `#wersje-testowe`, `#zrzuty-i-klipy` i `#autor-notatki`; dodasz je, gdy będzie ruch. Minimum to: `#start`, `#ogłoszenia`, `#przedstaw-się`, `#zgłoszenia`, `#nagrania`, `#pomysły`, `#off-topic`, głosowy.

Kanał typu „ogłoszeniowy” (Discord: Announcement) pozwala testerom „śledzić” kanał na własnych serwerach; jeśli serwer nie ma włączonej Społeczności, zostaw zwykły tekstowy z uprawnieniami tylko dla Ciebie.

## 3. Role i uprawnienia

| Rola | Kolor | Kto | Uprawnienia ponad @everyone |
| --- | --- | --- | --- |
| Autor | czerwony | Ty | Administrator |
| Moderator | pomarańczowy | 1–2 zaufane osoby, gdy serwer urośnie | Zarządzaj wiadomościami, Zarządzaj wątkami, Wyrzucaj członków, Moderuj członków (timeout) |
| Tester | cyjan | każdy po przedstawieniu się | Wyświetl kanały TESTY i SPOŁECZNOŚĆ, Załączaj pliki, Osadzaj linki, Twórz wątki publiczne, Dodawaj reakcje, Używaj poleceń aplikacji |
| Tester PRO | fioletowy | osoby, które przysłały 3 nagrania z formularzem | jak Tester + dostęp do #wersje-testowe; wyróżnienie na liście |
| @everyone | brak | każdy z linku | Wyświetl #start, #ogłoszenia, #przedstaw-się, #faq; Czytaj historię; Wysyłaj wiadomości tylko w #przedstaw-się |

Ustawienie `@everyone`: Ustawienia serwera → Role → @everyone → wyłącz „Wysyłaj wiadomości”, „Załączaj pliki”, „Twórz zaproszenia” (zaproszenia robisz Ty, z limitem użyć), „Zmieniaj pseudonim” zostaw włączone.

Nadawanie roli Tester: klik na nick w `#przedstaw-się` → Role → Tester. Jedno zdanie od osoby wystarczy; chodzi o to, żeby boty i przypadkowi goście z Facebooka nie weszli do kanałów testowych.

Poziom weryfikacji serwera: „Średni” (konto starsze niż 5 minut). Filtr treści: „Skanuj wiadomości od wszystkich”. Tryb Społeczności: na razie wyłączony (wymaga kanału zasad i otwiera serwer szerzej); włączysz go w fazie publicznej.

## 4. Boty: co jest potrzebne, a co nie

Na 10–30 testerów nie potrzebujesz żadnego bota zewnętrznego. Wszystko, co ważne, robi sam Discord:

| Potrzeba | Rozwiązanie bez bota | Bot dopiero gdy |
| --- | --- | --- |
| wpisy o nowych wersjach z GitHuba | wbudowany webhook: Ustawienia kanału #dziennik-zmian → Integracje → Webhooki → Nowy webhook → skopiuj URL; w repozytorium GitHub: Settings → Webhooks → Add webhook, URL z końcówką `/github`, zdarzenia: Pushes, Releases | nigdy, webhook wystarczy |
| filtr spamu i linków | wbudowany AutoMod: Ustawienia serwera → AutoMod → włącz „Blokuj spam” i „Blokuj podejrzane linki”, dodaj regułę na wzmianki (ponad 5 w wiadomości) | nigdy w tej skali |
| rola po przedstawieniu się | ręcznie, 2 kliknięcia | powyżej ok. 50 osób: Carl-bot albo MEE6 (reakcja pod wiadomością w #start nadaje rolę Tester) |
| ankiety | wbudowane ankiety Discorda (ikona + przy polu wiadomości) | nigdy |
| statystyki serwera | zakładka Insights w ustawieniach (po włączeniu Społeczności) | nigdy |
| przypomnienia o sesjach | wbudowane Wydarzenia (ikona kalendarza) | nigdy |
| moderacja | AutoMod + rola Moderator + timeouty | powyżej 100 osób: Dyno albo Carl-bot do logów i ostrzeżeń |

Jeśli kiedyś dojdzie bot, zasady: tylko jeden, z oficjalnej strony bota (nie z linku od użytkownika), z minimalnymi uprawnieniami (bez Administratora), dodany na kanał `#zaplecze`, nie na cały serwer. Bot ma dostęp do treści serwera, więc to samo, co wpuszczenie kogoś z zewnątrz.

Czego nie dodawać: botów muzycznych, botów z poziomami i XP, botów „powitalnych” z grafikami. Hałas bez pożytku w serwerze testowym.

## 5. Onboarding testera, krok po kroku

1. Osoba wchodzi z linku, widzi `#start` z przypiętym powitaniem i `#przedstaw-się`.
2. Pisze jedno zdanie w `#przedstaw-się` (szablon w części 6).
3. Ty nadajesz rolę Tester. Od tej chwili widzi TESTY i SPOŁECZNOŚĆ.
4. Pobiera paczkę z `#ogłoszenia`, przechodzi `CZYTAJ-TO.txt`, jedzie pierwszą sesję.
5. Po sesji: wątek w `#nagrania` (formularz + zrzut + link do nagrania), błędy w `#zgłoszenia`.
6. Po trzech nagraniach z formularzem: rola Tester PRO i dostęp do `#wersje-testowe`.

Limity plików: Discord bez boostów przyjmuje załączniki do 10 MB. Zrzuty i formularze się mieszczą, nagrania po `spakuj.bat` (części po 20 MB) nie. Nagrania idą przez GitHub albo dysk w chmurze, a w wątku na Discordzie jest tylko link. Jeśli wolisz wszystko na Discordzie, dzielenie w `spakuj.bat` można zmniejszyć do 9 MB.

## 6. Treści do wklejenia

Po wklejeniu: przytrzymaj wiadomość (telefon) albo prawy klik (komputer) → Przypnij.

### #start (przypięte)

```
Cześć! To zamknięte testy BoxBox Academy, trenera jazdy do F1 25.
Program czyta telemetrię gry na Twoim komputerze i mówi głosem mechanika, co poprawić
w zakrętach, w którym sektorze tracisz czas i co zrobić na następnym okrążeniu.
Nic nie wysyła do sieci, dane zostają u Ciebie.

JAK ZACZĄĆ
1. Napisz jedno zdanie w #przedstaw-się. Dostaniesz rolę Tester i zobaczysz resztę kanałów.
2. Pobierz paczkę z #ogłoszenia i rozpakuj. Potrzebny Python 3.12 lub nowszy
   (python.org, przy instalacji zaznacz "Add python.exe to PATH").
3. Uruchom akademia.bat. Gdy Windows ostrzega, zobacz docs\BoxBox_Academy_antywirus.pdf w paczce.
4. W grze: Ustawienia -> Telemetria UDP włączona, port 20777, adres 127.0.0.1, format 2025 albo 2026.
   Dla nakładki HUD gra w oknie bez ramki.
5. Przejdź kreator, kliknij JEDŹ, jedź trening. Pierwsze okrążenie to odniesienie, od drugiego mechanik mówi.

GDZIE CO
#zgłoszenia - błędy (szablon w wytycznych kanału)
#nagrania - nagrania sesji z formularzem (docs\formularze w paczce)
#pomysły - propozycje
#off-topic - reszta

Obsługiwane: F1 25 i 2026 Season Pack na PC. F1 23/24 nie. Wersja programu jest w lewym dolnym
rogu okna, podawaj ją w każdym zgłoszeniu. Dzięki, że jesteś!
```

### #ogłoszenia (pierwszy wpis)

```
Paczka testowa 0.7.0-beta: [link do ZIP]

W środku: program, CZYTAJ-TO.txt z czterema krokami startu, PDF-y w docs:
co nagrać, formularze, antywirus, dokumentacja.

Co nowego względem posta na Facebooku:
- model zakrętów: cel na każdy zakręt liczony z wielu czystych okrążeń (MAD + średnia ważona + EMA),
  najlepsze okrążenie zostaje jako drugi punkt odniesienia
- po okrążeniu: sektor z największą stratą i konkretne polecenie, np. "zacznij hamować wcześniej, o 20 m"
- sektory S1-S3 w panelu na żywo i w podsumowaniu, moduł DRS/bateria/sektory na HUD

Na czym mi najbardziej zależy w tej rundzie: trening na Monzy (8-10 okrążeń) z formularzem
i wyścig z AI na 5 okrążeń. Szczegóły w docs\BoxBox_Academy_co_nagrac.pdf.
```

### #przedstaw-się (przypięte)

```
Jedno zdanie wystarczy, np.:
"Cześć, jeżdżę w F1 25 na padzie, TC pełna, ABS wł., głównie Time Trial na Monzy i Bahrajnie.
Format UDP 2026." Po wpisie dostajesz rolę Tester.
```

### #zgłoszenia (wytyczne postów forum)

```
Tytuł wątku: krótko, co się dzieje, np. "Brak komunikatów po 3. okrążeniu na Suzuce".
W treści:
Wersja (lewy dolny róg okna):
Tor, tryb w grze, format UDP (2025/2026):
Asysty (skrzynia / TC / ABS):
Co zrobiłem:
Co się stało:
Czego się spodziewałem:
Zrzut ekranu albo film:
ZIP z "Pomoc i wsparcie -> Raport błędu" (jeśli program nie działa albo mechanik milczy):
Tag: błąd / pytanie / działa. Gdy naprawione, zmieniam tag na "naprawione" i zamykam wątek.
```

### #nagrania (wytyczne postów forum)

```
Jeden wątek na jedną sesję. Tytuł: tor i tryb, np. "Monza trening, 9 okrążeń".
W wątku:
1. Wypełniony formularz z docs\formularze (txt albo wklejony tekst).
2. Zrzut Podsumowania sesji (zakładka Start po zakończeniu).
3. Link do nagrania .bin.xz (po spakuj.bat) albo informacja, że poszło na GitHub.
Nagrania zawierają tylko telemetrię gry, nazwy graczy są usuwane przy zapisie.
Najważniejsze są Twoje odczucia: czy podpowiedzi przyszły na czas i czy pasowały do sytuacji.
```

### #pomysły (wytyczne postów forum)

```
Jeden wątek na jeden pomysł. Napisz: co ma robić, kiedy (w trakcie jazdy / po okrążeniu / po sesji)
i jaki problem rozwiązuje. Przed założeniem wątku sprawdź, czy ktoś już tego nie zgłosił: dopisz się
reakcją zamiast dublować. Tag: trener / okno / HUD / głos / inne.
```

### #faq (pierwszy wpis, uzupełniany)

```
Czy program wysyła coś do sieci? Nie. Słucha tylko telemetrii gry na tym komputerze. Dane są w folderze data obok programu.
Skąd są podpowiedzi? Z Twojej telemetrii: porównanie z celem na zakręt policzonym z Twoich czystych okrążeń
i z Twoim najlepszym okrążeniem. Nic nie jest generowane przez model językowy; głos to nagrane wcześniej zdania.
Czy działa z F1 23 / F1 24? Nie, tylko F1 25 i 2026 Season Pack (formaty UDP 2025 i 2026).
Mechanik milczy. Sprawdź: telemetria UDP włączona w grze, port 20777, pastylka w oknie zielona,
klipy w assets\voice. Pierwsze okrążenie jest zawsze ciche (odniesienie).
Windows blokuje plik. docs\BoxBox_Academy_antywirus.pdf w paczce.
Jak odinstalować? Usuń folder. Program nie zapisuje niczego poza swoim folderem.
```

### Wytyczne dla roli Moderator (do #autor-notatki, gdy dojdzie moderator)

```
Przenoś błędy wrzucone w #off-topic do #zgłoszenia (odpowiedz linkiem, poproś o wątek).
Nie usuwaj wiadomości testerów poza spamem i treściami z danymi osobowymi (klucze, adresy, nazwiska w zrzutach).
Timeout 1 h za spam, dłużej tylko po uzgodnieniu z Autorem.
Nie odpowiadaj za Autora na pytania o plany i terminy, kieruj do #ogłoszenia.
```

## 7. Konfiguracja krok po kroku (komputer)

1. Ustawienia serwera → Przegląd: logo z `assets/`, nazwa „BoxBox Academy”.
2. Ustawienia serwera → Bezpieczeństwo: weryfikacja „Średni”, filtr treści „Wszyscy”.
3. Ustawienia serwera → Role: utwórz Autor (Administrator), Tester, Tester PRO, Moderator jak w części 3; @everyone bez „Wysyłaj wiadomości”.
4. Utwórz kategorie INFO, TESTY, SPOŁECZNOŚĆ, ZAPLECZE. W TESTY, SPOŁECZNOŚĆ i ZAPLECZE: Uprawnienia kategorii → @everyone „Wyświetl kanał” X, Tester „Wyświetl kanał” ✓; dla kanałów w kategorii „Synchronizuj uprawnienia”.
5. Utwórz kanały z tabeli w części 2; `#zgłoszenia`, `#nagrania`, `#pomysły` jako Forum z tagami.
6. `#ogłoszenia`, `#start`, `#faq`: Uprawnienia → @everyone „Wysyłaj wiadomości” X, „Twórz wątki” X, „Wyświetl kanał” ✓. `#przedstaw-się`: @everyone „Wysyłaj wiadomości” ✓, „Załączaj pliki” X.
7. AutoMod: włącz „Blokuj spam” i „Blokuj podejrzane linki”.
8. Webhook GitHub do `#dziennik-zmian` (część 4), zdarzenia Pushes i Releases.
9. Wklej i przypnij treści z części 6.
10. Przejdź ścieżkę na drugim koncie: bez roli widoczne tylko INFO i `#start`; po roli Tester reszta.
11. Zaproszenie: Ustawienia serwera → Zaproszenia → nowy link, limit 25 użyć, bez wygaśnięcia. Wyślij czterem osobom z komentarzy pod postem.

## 8. Faza publiczna (później)

Gdy beta wyjdzie na GitHub Releases: włącz tryb Społeczności (kanał zasad i ogłoszeń systemowych są wymagane), dodaj `#zasady` (krótkie: szacunek, bez spamu, bez danych osobowych, bez piractwa), `#pobieranie` z aktualnym linkiem i sumą kontrolną, `#pomoc` otwarte dla wszystkich (bez roli), bota do roli przez reakcję (Carl-bot), ewentualnie kanał po angielsku, gdy pojawią się zagraniczni użytkownicy. Struktura testowa zostaje bez zmian, tylko kategoria TESTY wymaga wtedy roli Tester nadawanej za aktywność, nie za samo wejście.
