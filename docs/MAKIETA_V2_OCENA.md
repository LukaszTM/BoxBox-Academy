# Makieta v2 i HUD v2 – ocena i lista koniecznych zmian

Dotyczy plików: `BoxBox_Academy_Makieta_v2_INTERAKTYWNA.html`, `BoxBox_Academy_HUD_v2.html`,
paczek `v2_KOMPLET.zip` i `v2_PODGLADY.zip` z 27.10.2026.

## 1. Werdykt

Makieta v2 i HUD v2 **nadają się do implementacji**. Oba pliki realizują wszystkie punkty briefu
(A1–A6, pasek komunikatów B, braki C7–C11, HUD D1–D7). Są samowystarczalne: jeden plik HTML, brak
skryptów z internetu, brak zależności zewnętrznych. Dzięki temu wchodzą do programu tą samą drogą co
v1: okno WebEngine z mostkiem danych, a `DataBuilder` dostarcza już prawie wszystkie pola, które
makieta pokazuje.

Poniżej tylko to, co trzeba zmienić lub rozstrzygnąć przed wdrożeniem. Punkty oznaczone **[K]** są
konieczne, **[Z]** to zalecane, **[D]** to decyzja do podjęcia przez Ciebie.

| Nr | Element | Waga | Jedno zdanie |
|---|---|---|---|
| 1 | Czcionka HUD | [K] | Arial Narrow nie jest częścią Windows; dołączamy własną czcionkę do paczki. |
| 2 | Tryb Wyścig | [D] | Program ma już tryb wyścigowy, przełącznik "Wyścig · wkrótce" można odblokować. |
| 3 | Rozszerzone kanały | [Z] | Bieg, kierownica, ERS i delta są w telemetrii, wykresy mogą być prawdziwe od razu. |
| 4 | Delta czasu | [K] | Delta to jedna linia wokół zera, nie para linii jak inne kanały. |
| 5 | Mapy torów | [K] | Obrys z recordera, makieta daje tylko styl markerów. |
| 6 | Drobny tekst | [Z] | 10–11 px podnieść do 12 px przy przenoszeniu. |
| 7 | Pozycje HUD | [K] | Domyślne pozycje ustawić na prawdziwych zrzutach z F1 25. |
| 8 | Stan "po okrążeniu" | [K] | Znika sam po 6 s, nie pokazuje się na okrążeniu z boksu. |
| 9 | Minimapa HUD | [K] | Z kształtu recordera; bez kształtu moduł ukryty. |
| 10 | Tło i link online | [K] | Tylko w podglądzie; program nie łączy się z internetem. |
| 11 | Tryb okna gry | [K] | Nakładka widoczna tylko w trybie "okno bez ramki"; dopisać do samouczka. |

## 2. Makieta programu v2 – co zostaje bez zmian

- Dwa stany Startu (przed pierwszą sesją i po sesji) oraz stan "Sesja na żywo" z paskiem u góry
  i przyciskami *Podgląd nakładki* i *Zakończ sesję*. Pasuje do auto-startu programu.
- Pasek komunikatów pod nagłówkiem: błąd trwały, informacja i sukces na 6 s, przycisk akcji,
  krzyżyk. Zastępuje dotychczasowe toasty w rogu.
- Stany puste Startu, Analizy, Postępu i wykresu pierwszego okrążenia: ikona, jedno zdanie, jeden
  przycisk.
- Samouczek 7 kroków w dymkach przy elementach z licznikiem i przyciskami *Zamknij* i *Dalej*.
- Postęp: trend czasów właściwego toru, najlepsze czasy per krok asyst, zakręty opanowane i do
  pracy, kamienie milowe, tabela historii z sortowaniem i wyróżnionym najlepszym czasem.
- Analiza: kanały, mapa toru z klikalnym zakrętem, uwagi mechanika powiązane z zakrętem, przyciski
  *Eksport CSV* i *Drukuj PDF*, stan "Brak pliku" dla toru bez kształtu.
- Plakietka kierowcy w stylu prawa jazdy na ekranie głównym, klik otwiera Kartę kierowcy.
- Ustawienia → Dane z folderami, licznikami i raportem błędu.
- Wygląd: szkło, poświaty, gradienty, głębia. Zgodne z wytycznymi marki.

## 3. Makieta programu v2 – zmiany

### 3.1 Tryb Wyścig [D]

W makiecie przełącznik "Wyścig · wkrótce" jest wyszarzony. Program ma już tryb wyścigowy
(inżynier na radiu: flagi, SC, DRS, okno pitstopu, opony, uszkodzenia, start). Proponuję odblokować
przełącznik od razu w becie i usunąć dopisek "wkrótce". Jeśli wolisz zostawić wyścig na później,
zostaje tak jak w makiecie.

### 3.2 Rozszerzone kanały w Analizie [Z]

Blok "Rozszerzone kanały" jest opisany jako podgląd przyszłych analiz. Bieg, kąt kierownicy,
poziom ERS i delta czasu są już w telemetrii i w bazie. Wykresy mogą pokazywać prawdziwe dane od
pierwszej wersji; układ z makiety zostaje.

### 3.3 Delta czasu [K]

Delta czasu w makiecie wygląda jak pozostałe kanały (dwie linie: kierowca i referencja). Delta to
jedna linia wokół osi zero: powyżej zera gracz traci, poniżej zyskuje. Linia zielona pod zerem,
czerwona nad zerem, oś zero pozioma, podpis "−0,41 s" na końcu.

### 3.4 Mapy torów [K]

Obrysy Monzy, Bahrajnu i Suzuki w makiecie są demonstracyjne. W programie obrys przychodzi z
recordera (plik kształtu toru). Z makiety przejmujemy wyłącznie styl: grubość linii, kolor,
czerwone punkty hamowania gracza, szare referencji, podświetlenie wybranego zakrętu, mały wskaźnik
DRS, znacznik start/meta. Stan "Brak pliku" zostaje.

### 3.5 Drobny tekst [Z]

W makiecie nadal jest kilkadziesiąt miejsc z tekstem 10–11 px (podpisy w tabelach, legendy,
podpisy osi). Na 1080p jest czytelny, ale to poniżej progu A1 z briefu. Przy przenoszeniu podnoszę
do 12 px, układ się nie zmienia.

### 3.6 Elementy demonstracyjne

Pasek "STANY MAKIETY V2", przycisk "DEMO UI", napis "Tryb demonstracyjny", stopka "DESIGN
CONCEPT / V2" i wszystkie dane przykładowe znikają przy wdrożeniu. Nie wymaga decyzji.

## 4. HUD v2 – co zostaje bez zmian

- Styl grafik telewizyjnych F1: wstęgi ze ścięciem 45°, pasek akcentowy z lewej, liczby
  tabelaryczne, brak ramek i tła między modułami.
- Siedem modułów z osobnymi identyfikatorami (status, corner, goal, timing, radio, minimap,
  lapend). Pozycje w procentach ekranu 16:9, co przenosi się 1:1 na przezroczyste okno
  pełnoekranowe.
- Krycie 0–100 %, skala 65–160 %, ukrywanie modułów, tryb przeciągania.
- Trzy stany: na żywo, po okrążeniu, czekam na grę ("Czekam na grę · port 20777").

Edycja pozycji odbywa się w zakładce *HUD F1* w programie, na statycznym podglądzie, nie w grze.
Zgodne z zasadą "wszystko w programie, bez wyskakujących okien".

## 5. HUD v2 – zmiany

### 5.1 Czcionka [K]

HUD v2 używa 'Arial Narrow'. Ta czcionka nie jest częścią Windows: dostarcza ją pakiet Microsoft
Office. Na komputerze bez Office przeglądarka w programie przełącza się na Segoe UI lub Arial,
wstęgi robią się o 30–40 % szersze i zaczynają nachodzić na HUD gry. Dolny wiersz na ilustracji
pokazuje ten przypadek. Dlatego dołączamy własną czcionkę do paczki programu (propozycja w
rozdziale 6).

### 5.2 Domyślne pozycje modułów [K]

Pozycje w makiecie są ustawione na ilustracji, nie na obrazie z gry. Dwa miejsca wymagają
sprawdzenia na prawdziwych zrzutach z F1 25:

- moduł *status* w lewym górnym rogu może nachodzić na wieżę pozycji gry;
- moduł *timing* w prawym górnym rogu w widoku z kokpitu może zasłaniać lusterko.

Potrzebuję od Ciebie zrzutów z F1 25 w 1920×1080: widok z kokpitu, widok TV, widok z maski, na
torze z aktywnym HUD gry. Na ich podstawie ustawię domyślne pozycje. Gracz i tak może je przesunąć.

### 5.3 Stan "po okrążeniu" [K]

W makiecie stan przełącza się ręcznie. W programie: pojawia się po przejechaniu linii mety, znika
sam po 6 s, nie pojawia się na okrążeniu wyjazdowym z boksu ani po okrążeniu niepełnym. Moduły
*corner* i *goal* są w tym czasie przyciemnione tak jak w makiecie.

### 5.4 Moduł "goal" (POPRAW) [K]

Doprecyzowanie, którego brakuje w makiecie: wstęga "Na tym okrążeniu popraw" pokazuje się od
startu okrążenia, podświetla się na 300 m przed wskazanym zakrętem i znika po jego przejechaniu.
Tekst przychodzi z silnika (cel na następne okrążenie).

### 5.5 Minimapa [K]

Minimapa w HUD z kształtu recordera, tak jak mapa w Analizie. Na torze bez kształtu moduł jest
ukryty, nie pokazuje obrysu zastępczego.

### 5.6 Tło i obraz z internetu [K]

Ilustracja z bolidem i opcjonalny zrzut z serwisu internetowego służą tylko podglądowi w
przeglądarce. W programie tło nakładki jest przezroczyste. Program nie łączy się z internetem,
więc link do zrzutu online nie trafia do kodu. Do podglądu w zakładce *HUD F1* użyjemy Twojego
zrzutu z gry (pkt 5.2).

### 5.7 Tryb okna gry [K]

Ograniczenie techniczne, nie wada makiety: każda nakładka, także ta, jest widoczna tylko gdy gra
działa w trybie "okno bez ramki" (Borderless). W pełnym ekranie wyłącznym gra zasłania wszystko.
Dopisujemy to do samouczka (krok "Nakładka") i do Pomocy, a program przy pierwszym uruchomieniu
nakładki pokazuje pasek informacji z tym zdaniem.

## 6. Propozycja czcionki

Wymagania: darmowa licencja pozwalająca dołączyć plik do programu (SIL Open Font License), pełne
polskie znaki, krój zwężony do wstęg HUD, liczby tabelaryczne (ta sama szerokość cyfr, żeby czas
okrążenia nie "skakał"), wersja zwykła do tekstu programu.

![Porównanie: trzy kandydatki w wstęgach HUD v2, dolny wiersz to HUD z makiety bez Arial Narrow, na dole Inter jako tekst programu.](docs/img/makieta_v2_czcionki.png)

| Czcionka | Licencja | Charakter | Ocena |
|---|---|---|---|
| **Barlow Condensed** | OFL | Zwężona, zaokrąglone narożniki, bardzo blisko Arial Narrow z makiety, dobre cyfry | **Propozycja główna.** Najbliższa temu, co już narysowałeś; wstęgi zachowują szerokość z makiety. |
| Titillium Web | OFL | Geometryczna, szersza, popularna w nakładkach sim-racingowych | Dobra czytelność, ale wstęgi robią się o 20 % szersze niż w makiecie. |
| Saira Condensed | OFL | Zwężona, kanciasta, najbardziej "techniczna" | Bardzo dobra w liczbach, mniej przyjazna w dłuższych zdaniach. |

Rekomendacja:

- **HUD i duże liczby w programie** (czas okrążenia, delta, nazwa zakrętu, nagłówki wstęg):
  *Barlow Condensed* w odmianach Medium (500) i SemiBold (600).
- **Tekst programu** (opisy, tabele, ustawienia): *Inter* w odmianach 400–700 zamiast Segoe UI.
  Inter ma identyczny charakter, a dzięki dołączeniu pliku program wygląda tak samo na każdym
  komputerze, także bez Segoe UI w nowszych wersjach Windows.
- Oba kroje są na licencji OFL: wolno je dołączyć do paczki i do instalatora bez opłat; do paczki
  trafia też plik licencji.

Alternatywa, jeśli wolisz wygląd bliższy transmisjom F1 TV: oficjalny krój F1 jest zastrzeżony i
nie wolno go dołączyć, ale *Titillium Web* daje podobny, geometryczny charakter. Wtedy wstęgi HUD
trzeba poszerzyć o 20 % i domyślne pozycje ustawić od nowa.

## 7. Co potrzebuję przed wdrożeniem

1. Wybór czcionki: Barlow Condensed + Inter (rekomendacja) albo Titillium Web + Inter.
2. Zrzuty z F1 25 w 1920×1080 (kokpit, TV, maska) z włączonym HUD gry.
3. Decyzja o trybie Wyścig: odblokować w becie czy zostawić "wkrótce".

## 8. Kolejność wdrożenia po Twoim "tak"

1. Przeniesienie makiety v2 do programu: pasek komunikatów, dwa stany Startu, stany puste, samouczek, Ustawienia → Dane, poprawki Postępu i Analizy, czcionki w paczce.
2. HUD jako przezroczyste okno pełnoekranowe: siedem modułów, trzy stany, krycie i skala, pozycje zapisane w ustawieniach, zakładka *HUD F1* z edytorem na podglądzie.
3. Testy na nagraniach z Monzy i protokół testów partii 2.
