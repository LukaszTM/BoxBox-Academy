"""Importuje obrysy torów z paczki „BoxBox_Academy_Tory_F1_2025_HUD” do boxbox/tracks/atlas/<track_id>.json.

Bierzemy wyłącznie geometrię (polilinia z projektu f1-circuits, licencja MIT). Zakręty, sektory i DRS
z paczki pomijamy: mają inną licencję (CC BY-NC-SA) i nie zgadzają się z grą (sprawdzone na nagraniach).
Użycie: python tools/import_atlas.py <folder_paczki_z_katalog_torow_2025.json>
       python tools/import_atlas.py --geojson <plik.geojson> <track_id> <nazwa_pl>   (np. Madring z f1-circuits dla sezonu 2026)
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATLAS_DIR = ROOT / "boxbox" / "tracks" / "atlas"

# identyfikator toru w telemetrii F1 25 -> slug w paczce (docs/LISTA_TOROW.md)
TRACK_IDS = {
    0: "melbourne", 2: "shanghai", 13: "suzuka", 3: "bahrain", 29: "jeddah", 30: "miami", 27: "imola", 5: "monaco",
    4: "barcelona", 6: "montreal", 17: "red-bull-ring", 7: "silverstone", 10: "spa-francorchamps", 9: "hungaroring",
    26: "zandvoort", 11: "monza", 20: "baku", 12: "singapore", 15: "circuit-of-the-americas", 19: "mexico-city",
    16: "interlagos", 31: "las-vegas", 32: "losail", 14: "yas-marina",
    # układy odwrócone (tylko F1 25): ten sam obrys, jazda w drugą stronę
    39: "silverstone", 40: "red-bull-ring", 41: "zandvoort",
}
NAMES_PL = {
    "melbourne": "Melbourne", "shanghai": "Szanghaj", "suzuka": "Suzuka", "bahrain": "Bahrajn", "jeddah": "Dżudda", "miami": "Miami",
    "imola": "Imola", "monaco": "Monako", "barcelona": "Barcelona", "montreal": "Montreal", "red-bull-ring": "Austria", "silverstone": "Silverstone",
    "spa-francorchamps": "Spa", "hungaroring": "Hungaroring", "zandvoort": "Zandvoort", "monza": "Monza", "baku": "Baku", "singapore": "Singapur",
    "circuit-of-the-americas": "Austin", "mexico-city": "Meksyk", "interlagos": "Interlagos", "las-vegas": "Las Vegas", "losail": "Katar", "yas-marina": "Abu Zabi",
}


def main(src: Path) -> None:
    catalog = json.loads((src / "katalog_torow_2025.json").read_text(encoding="utf-8"))
    by_slug = {t["slug"] if "slug" in t else Path(t["data"]).parent.name.split("_", 1)[1]: t for t in catalog["tracks"]}
    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    for track_id, slug in sorted(TRACK_IDS.items()):
        item = by_slug[slug]
        data = json.loads((src / item["data"]).read_text(encoding="utf-8"))
        doc = {
            "track_id": track_id, "slug": slug, "name": NAMES_PL[slug], "full_name": data["name"], "length_m": data["length_m"],
            "coords": "0..1000, y w dół, północ u góry; ta sama orientacja co świat F1 25 (x, z)",
            "source": "f1-circuits (Tomislav Bacinger, MIT) przez paczkę BoxBox_Academy_Tory_F1_2025_HUD; uproszczona polilinia",
            "points": [[round(float(x), 2), round(float(y), 2)] for x, y in data["points_xy"]],
        }
        (ATLAS_DIR / f"{track_id}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        print(f"{track_id:>3} {slug:<24} {len(doc['points'])} punktów")


def from_geojson(path: Path, track_id: int, name: str) -> None:
    """GeoJSON (lon/lat) z f1-circuits -> ten sam układ co paczka: 0..1000, y w dół, północ u góry, proporcje zachowane."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    feat = doc["features"][0]
    geom = feat["geometry"]
    coords = geom["coordinates"] if geom["type"] == "LineString" else geom["coordinates"][0]
    if coords[0] == coords[-1]:
        coords = coords[:-1]  # polilinia zamknięta: ostatni punkt dubluje pierwszy
    lat0 = sum(c[1] for c in coords) / len(coords)
    xs = [c[0] * math.cos(math.radians(lat0)) for c in coords]
    ys = [-c[1] for c in coords]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    k = 920.0 / span
    pts = [[round(40 + (x - min(xs)) * k, 2), round(40 + (y - min(ys)) * k, 2)] for x, y in zip(xs, ys)]
    out = {
        "track_id": track_id, "slug": feat["properties"].get("id", path.stem), "name": name, "full_name": feat["properties"].get("Name", name),
        "length_m": int(feat["properties"].get("length", 0)),
        "coords": "0..1000, y w dół, północ u góry; ta sama orientacja co świat F1 25 (x, z)",
        "source": "f1-circuits (Tomislav Bacinger, MIT), plik " + path.name,
        "points": pts,
    }
    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    (ATLAS_DIR / f"{track_id}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"{track_id:>3} {out['slug']:<24} {len(pts)} punktów, {out['length_m']} m")


if __name__ == "__main__":
    if sys.argv[1] == "--geojson":
        from_geojson(Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    else:
        main(Path(sys.argv[1]))
