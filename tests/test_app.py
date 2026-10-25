from boxbox.app import NO_DATA_MESSAGE, main


def test_app_prints_no_data(capsys) -> None:
    assert main([]) == 0
    assert NO_DATA_MESSAGE in capsys.readouterr().out
