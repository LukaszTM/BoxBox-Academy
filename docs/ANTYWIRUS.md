# BoxBox Academy – gdy Windows blokuje program

Plik `BoxBoxAcademy.exe` nie jest podpisany certyfikatem (podpis kosztuje kilkaset złotych rocznie
i w becie go nie ma). Windows pokazuje wtedy ostrzeżenie, a niektóre antywirusy przenoszą plik do
kwarantanny. To normalne dla programów zbudowanych PyInstallerem. Poniżej, co zrobić.

## 1. Skąd pobierać

Tylko z GitHuba projektu, z zakładki Releases. Plik z innego miejsca może być podmieniony.
Po pobraniu porównaj sumę kontrolną z tą w opisie wydania: w PowerShell wpisz
`Get-FileHash .\BoxBoxAcademy.exe -Algorithm SHA256` i porównaj wynik.

## 2. Niebieskie okno „System Windows ochronił ten komputer” (SmartScreen)

1. Kliknij **Więcej informacji**.
2. Pojawi się przycisk **Uruchom mimo to**. Kliknij go.
3. Okno pojawia się tylko przy pierwszym uruchomieniu tej wersji pliku.

Jeśli przycisku nie ma, SmartScreen jest ustawiony na blokowanie bez pytania:
Ustawienia → Prywatność i zabezpieczenia → Zabezpieczenia Windows → Kontrola aplikacji i przeglądarki
→ Sprawdzanie aplikacji i plików → **Ostrzegaj**.

## 3. Windows Defender usunął plik albo zgłasza zagrożenie

1. Otwórz **Zabezpieczenia Windows** → **Ochrona przed wirusami i zagrożeniami** → **Historia ochrony**.
2. Znajdź wpis z `BoxBoxAcademy.exe`, rozwiń go i wybierz **Akcje → Przywróć** (albo **Zezwól na urządzeniu**).
3. Dodaj folder programu do wyjątków: **Ustawienia ochrony przed wirusami i zagrożeniami → Zarządzaj ustawieniami
   → Wykluczenia → Dodaj wykluczenie → Folder** i wskaż folder, w którym leży `BoxBoxAcademy.exe`.
4. Uruchom program ponownie.

Wyjątek dla folderu wystarczy na kolejne wersje, jeśli będziesz je wgrywać w to samo miejsce.

## 4. Inny antywirus (Avast, AVG, Bitdefender, ESET, Kaspersky, Norton)

Każdy ma w ustawieniach listę wyjątków (wykluczeń). Dodaj do niej folder programu, tak jak w punkcie 3.
Jeśli plik trafił do kwarantanny, przywróć go z kwarantanny i dopiero wtedy dodaj wyjątek, inaczej
antywirus usunie go ponownie przy następnym skanie.

| Program | Gdzie szukać wyjątków |
| --- | --- |
| Avast / AVG | Menu → Ustawienia → Ogólne → Wyjątki |
| Bitdefender | Ochrona → Antywirus → Ustawienia → Zarządzaj wyjątkami |
| ESET | Ustawienia zaawansowane (F5) → Silnik detekcji → Wykluczenia |
| Kaspersky | Ustawienia → Zagrożenia i wykluczenia → Zarządzaj wykluczeniami |
| Norton | Ustawienia → Antywirus → Skanowanie i zagrożenia → Wykluczenia |

## 5. Co program robi, a czego nie robi

- Słucha telemetrii gry na porcie UDP 20777 na tym komputerze. Nie wysyła niczego do sieci.
- Zapisuje dane w folderze `data` obok programu: baza SQLite, ustawienia, dziennik, raporty.
- Nagrania sesji trafiają do folderu `recordings`. Wysyłasz je tylko wtedy, gdy sam je skopiujesz.
- Nie zmienia ustawień systemu, nie instaluje usług, nie uruchamia się z Windowsem.

Jeśli po wykonaniu powyższych kroków program nadal nie startuje, spakuj raport błędu
(Pomoc i wsparcie → Raport błędu) i wyślij go razem z nazwą antywirusa i jego komunikatem.
