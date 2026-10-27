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
    assert seen["packets"] > 1000 and seen["messages"] and seen["progress"].startswith("Cel: ")
    assert "Mechanik:" in capsys.readouterr().out


def test_log_focus_and_goal_lines(tmp_path) -> None:
    from boxbox.app import focus_line, main, progress_line
    from boxbox.coach.rules import Message

    assert progress_line(1, 2).startswith("Cel: 3 czyste okrążenia z rzędu (2/3), potem: TC średnia")
    assert "bez asyst" in progress_line(4, 0)
    msgs = [Message(2, 1, "T1-T2", "brake_late", "Hamowanie za późno w T1-T2, o 50 m.", "h", 0.5),
            Message(2, 3, "T6", "throttle_early", "Gaz za wcześnie w T6.", "h", 1.2)]
    assert focus_line(msgs) == "Na tym okrążeniu popraw: T6, gaz za wcześnie w t6"
    assert focus_line([]) == ""
    db = tmp_path / "d" / "b.sqlite"
    assert main(["--replay", "recordings/monza-glos-test2_2026-10-26_232722.bin.xz", "--speed", "0", "--db", str(db)]) == 0
    text = (tmp_path / "d" / "boxbox.log").read_text(encoding="utf-8")
    assert "start:" in text and "trener: tor Monza" in text and "mechanik:" in text and "okrążenie" in text
