import socket

from boxbox.app import NO_DATA_MESSAGE, main


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_app_prints_no_data(capsys) -> None:
    assert main(["--port", str(_free_port()), "--duration", "0.3"]) == 0
    assert NO_DATA_MESSAGE in capsys.readouterr().out


def test_overlay_runs_telemetry_in_background(tmp_path, monkeypatch, capsys) -> None:
    """--overlay: telemetria w wątku, okno w głównym; tu zamiast okna czekamy na koniec odtwarzania."""
    import boxbox.app as app
    from boxbox.ui.overlay_model import SharedCoachState

    seen = {}

    def fake_overlay(shared: SharedCoachState, args) -> None:
        shared.stop.wait(60)
        with shared.lock:
            seen["packets"] = shared.packets
            seen["messages"] = list(shared.messages)
            seen["progress"] = shared.progress_line

    monkeypatch.setattr(app, "_run_overlay", fake_overlay)
    rc = app.main(["--replay", "recordings/monza-trening_2026-10-26_153411.bin.xz", "--speed", "0",
                   "--db", str(tmp_path / "o.sqlite"), "--overlay"])
    assert rc == 0
    assert seen["packets"] > 1000 and seen["messages"] and seen["progress"].startswith("krok ")
    assert "Mechanik:" in capsys.readouterr().out
