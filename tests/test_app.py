import socket

from boxbox.app import NO_DATA_MESSAGE, main


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_app_prints_no_data(capsys) -> None:
    assert main(["--port", str(_free_port()), "--duration", "0.3"]) == 0
    assert NO_DATA_MESSAGE in capsys.readouterr().out
