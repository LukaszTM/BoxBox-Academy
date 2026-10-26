# Dane torów

Jeden plik na tor, nazwa `<track_id>.json` (id z pakietu Session, patrz `boxbox/telemetry/session.py`).
Pliki powstają z nagrań: `python -m boxbox.tracks.detect recordings/<plik>.bin`.
Potem zakręty można poprawić ręcznie (nazwy, granice). Format: `boxbox/tracks/model.py`.
