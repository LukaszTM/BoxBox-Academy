# Atlas obrysów torów

`<track_id>.json`: uproszczona polilinia toru (0..1000, y w dół, północ u góry) z projektu
[f1-circuits](https://github.com/bacinger/f1-circuits) (Tomislav Bacinger, licencja MIT, patrz LICENSE_MIT.txt).
Identyfikatory torów jak w telemetrii F1 25 (docs/LISTA_TOROW.md); układy odwrócone 39-41 mają obrys toru bazowego.

Sezon 2025: 24 tory (import z paczki BoxBox_Academy_Tory_F1_2025_HUD, `tools/import_atlas.py <folder>`).
Sezon 2026: ten sam zestaw bez Imoli plus Madryt (42, `tools/import_atlas.py --geojson tools/data_madring_es-2026.geojson 42 Madryt`).

Program używa obrysu do mapy toru i minimapy, zanim gracz nagra realny ślad. Po przejechaniu kilku zakrętów
`boxbox/tracks/atlas.py` dopasowuje obrys do współrzędnych gry (skala, przesunięcie, meta, kierunek).
Zakręty, sektory i DRS nie pochodzą z atlasu: zakręty z plików torów (boxbox/tracks/data), reszta z telemetrii.
