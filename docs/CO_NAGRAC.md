# BoxBox Academy – co nagrać (partia 2)

Trzy nagrania, wszystkie przez okno programu (nie przez stary recorder). Każde to 15–20 minut jazdy.
Kolejność ma znaczenie: jeśli masz czas tylko na jedno, zrób nagranie 1.

## 0. Przed pierwszym nagraniem

1. Pobierz najnowszą wersję: w folderze repo `git pull origin claude/new-session-t6gmj8`.
2. W grze: Ustawienia telemetrii → Format UDP: **2026**, port 20777, adres 127.0.0.1, 60 Hz.
3. Jeśli chcesz mieć nakładkę HUD: tryb okna **Bez ramki**.
4. Uruchom program, wejdź na Start. Pastylka w prawym górnym rogu ma być zielona, gdy gra jest w garażu.
5. Na Starcie: **Nagrywaj sesję** włączone, **Tryb cicho** wyłączony, wpisz nazwę sesji z tabeli niżej.

| Nagranie | Nazwa sesji w programie | Tryb w programie | Czas |
| --- | --- | --- | --- |
| 1 | monza-nauka | Nauka | ok. 20 min |
| 2 | wyscig-ai-5 | Wyścig | ok. 15 min |
| 3 | madryt-auto | Nauka | ok. 15 min |
| 3a | monza-mistrz | Nauka (Time Trial z duchem z rankingu) | ok. 10 min |

Zasady wspólne dla wszystkich nagrań: bez flashbacku, bez zmiany asyst w trakcie, bez pauzy dłuższej niż 15 s (po 20 s ciszy program kończy sesję). Pogoda: sucho, dzień.

## 1. Monza, trening, tryb Nauka, 8–10 okrążeń

Cel: sprawdzić prowadzenie głosem w zakrętach (kiedy mechanik mówi „Lekki hamulec”, „Pół gazu”, „Pełny gaz”) i zebrać dość okrążeń do analizy umiejętności (minimum 5 pełnych).

- W grze: Grand Prix → Monza → Trening 1, AI 100 lub jak zwykle. Asysty jak zwykle jeździsz.
- W programie: tryb **Nauka**, nazwa `monza-nauka`, JEDŹ przed wyjazdem z garażu.
- Jedź 8–10 pełnych okrążeń w swoim tempie. Od drugiego okrążenia mechanik prowadzi w maksymalnie trzech zakrętach, które idą najgorzej.
- Nie poprawiaj się na siłę. Trener ma zobaczyć normalną jazdę i to, czy jego podpowiedzi coś zmieniają.
- Po sesji zajrzyj do zakładek **Umiejętności** i **Podsumowanie sesji**, kliknij **Zapisz raport PDF** w Umiejętnościach.

Na co zwrócić uwagę w notatkach:

- Czy podpowiedź w zakręcie przyszła w sam raz, za wcześnie czy za późno (i w którym zakręcie).
- Czy treść pasowała do sytuacji (np. „Pół gazu” tam, gdzie faktycznie trzeba było odpuścić).
- Czy komunikaty nachodziły na siebie albo mechanik mówił za dużo.
- Czy po okrążeniach była rada o DRS albo o oponach i czy miała sens.
- Czy wyniki w zakładce Umiejętności zgadzają się z Twoim odczuciem (co było dobre, co słabe).

## 2. Wyścig z AI, 5 okrążeń, tryb Wyścig

Cel: start, inżynier na radiu, dziennik kontaktów i podsumowanie wyścigu.

- W grze: Grand Prix → Bahrajn albo Monza → Wyścig, długość **5 okrążeń**. Kwalifikacje: jedno okrążenie albo pomiń.
- Ważne: startuj ze środka stawki, nie z pole position. Jeśli gra pozwala, ustaw pole startowe 8–12.
- Uszkodzenia: zmniejszone. Kolizje: włączone. Kary: włączone. Bez obowiązkowego pit-stopu.
- W programie: tryb **Wyścig**, nazwa `wyscig-ai-5`, JEDŹ przed wyjazdem na pola startowe.
- Jedź normalnie. Jeśli dojdzie do kontaktu, nie cofaj czasu, jedź dalej. Kontakty nie muszą się zdarzyć, nie wymuszaj ich.
- Dojedź do mety i zostaw program włączony, aż pokaże podsumowanie.

Na co zwrócić uwagę w notatkach:

- Jak poszedł start (falstart, zgaszony silnik, dobra reakcja) i co powiedział inżynier.
- Każdy kontakt: okrążenie, zakręt, kto w kogo, co robiłeś (hamowanie, prosta, zakręt).
- Kary i ostrzeżenia, jeśli były.
- Czy komunikaty inżyniera w trakcie wyścigu były na czas i czy były przydatne.
- Czy podsumowanie po wyścigu opisało kontakty tak, jak je pamiętasz.

## 3. Madryt, trening, 5–6 okrążeń, tryb Nauka

Cel: nowy tor z pakietu 2026, do którego program nie ma pliku zakrętów. Program sam wyznaczy zakręty po pierwszym pełnym okrążeniu i nazwie je T1, T2, ...

- W grze: Grand Prix → Madryt → Trening 1 albo Time Trial. Format UDP musi być 2026.
- W programie: tryb **Nauka**, nazwa `madryt-auto`.
- Pierwsze pełne okrążenie przejedź spokojnie i czysto, bo z niego program buduje mapę zakrętów. Potem 4–5 okrążeń jak zwykle.

Na co zwrócić uwagę w notatkach:

- Od którego okrążenia mechanik zaczął komentować zakręty.
- Czy liczba zakrętów T1..Tn zgadza się mniej więcej z torem i czy jakiś ważny zakręt pominął albo podzielił na dwa.
- Czy komentarze pasowały do miejsc, w których faktycznie hamujesz.

## 3a. Monza, Time Trial z duchem z rankingu, 3 okrążenia (krótkie, 10 min)

Cel: dać programowi „okrążenie najlepszych” na Monzy. Od tej chwili trener porównuje Cię też do najlepszych na świecie.

- W grze: Time Trial → Monza → z tablicy wyników wybierz ducha z pierwszej dziesiątki (najlepiej nr 1) i włącz go.
- W programie: tryb **Nauka**, nazwa `monza-mistrz`, Format UDP taki sam jak w nagraniu 1.
- Przejedź 3 okrążenia w swoim tempie. Duch musi przejechać całe okrążenie, więc nie przerywaj sesji wcześniej.
- Po sesji program powie „Mam okrążenie najlepszych na tym torze”, a w podsumowaniu pojawi się zdanie „Najlepsi na tym torze: …”.

Na co zwrócić uwagę w notatkach:

- Czy komunikat o stracie do najlepszych („tracisz około … sekund, najwięcej w zakręcie …”) brzmiał sensownie.
- Czy wskazówka (hamują później / gaz wcześniej / szybszy apeks) zgadza się z tym, co widzisz u ducha.
- Czy rozbicie na warunki (paliwo, opony) pod kafelkiem „Do najlepszych” ma sens.

## 4. Po każdym nagraniu

Testerzy: zgłoszenia, formularze i pytania na Discordzie: https://discord.gg/t82VhVkVq

1. Zakończ sesję przyciskiem **Zakończ sesję** albo zjedź do garażu i poczekaj 20 s.
2. Plik nagrania jest w `recordings\<nazwa>_<data>.bin`. Obok może być `.guide.json`, wyślij go też.
3. Spakuj plik: w folderze repo `spakuj.bat recordings\<plik>.bin`. Powstanie `.bin.xz` (albo części, jeśli jest duży).
4. Wyślij `.bin.xz`, części i `.guide.json` tak samo jak klipy głosu: dodaj do repo i wypchnij na gałąź `claude/new-session-t6gmj8`.
5. Notatki wpisz w czacie albo do pliku `.txt` o tej samej nazwie obok nagrania (wzór niżej).
6. Zrzuty ekranu Podsumowania, Umiejętności i Karty kierowcy przyślij w czacie, nie do repo.

Wzór notatek:

```
Nagranie: monza-nauka
Asysty (skrzynia / TC / ABS): automat / średnia / wł.
Okrążenia: 9 pełnych, jedno przerwane (żwir w Z1 na 6. okr.)
Podpowiedzi w zakrętach:
3, Z1 (szykana), "Mocny hamulec" w sam raz
4, Z7 (Lesmo 2), "Pół gazu" za późno, już byłem w zakręcie
5, Z11 (Parabolica), "Lekki hamulec" OK, ale od razu potem komunikat o oponach
Rady po okrążeniach: DRS tak (sensowna), opony nie było
Umiejętności: hamowanie 62, wyjścia 48, zgadza się z odczuciem
Uwagi: po 7. okrążeniu mechanik zamilkł na dwa okrążenia
```
