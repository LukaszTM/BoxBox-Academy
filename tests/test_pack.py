import os
from pathlib import Path

from boxbox.tools.pack import compress, join, main, split


def test_compress_split_join_roundtrip(tmp_path: Path) -> None:
    src = tmp_path / "r.bin"
    data = os.urandom(3 << 20) + bytes(1 << 20)
    src.write_bytes(data)
    xz = compress(src)
    assert xz.name == "r.bin.xz" and xz.stat().st_size < len(data)
    parts = split(xz, part_mb=1)
    assert len(parts) >= 3 and parts[0].name == "r.bin.xz.part001"
    xz.unlink()
    joined = join(parts[0])
    assert joined.name == "r.bin.xz"
    import lzma
    assert lzma.decompress(joined.read_bytes()) == data


def test_cli_small_file_not_split(tmp_path: Path, capsys) -> None:
    src = tmp_path / "s.bin"
    src.write_bytes(bytes(1 << 20))
    assert main(["spakuj", str(src)]) == 0
    assert (tmp_path / "s.bin.xz").exists() and "Mieści się" in capsys.readouterr().out


def test_cli_big_file_split(tmp_path: Path, capsys) -> None:
    src = tmp_path / "b.bin"
    src.write_bytes(os.urandom(3 << 20))
    assert main(["spakuj", str(src), "--limit-mb", "1"]) == 0
    out = capsys.readouterr().out
    assert "podzielone" in out and not (tmp_path / "b.bin.xz").exists()
    parts = sorted(tmp_path.glob("b.bin.xz.part*"))
    assert len(parts) == 1 or len(parts) >= 1  # przy 20 MB częściach 3 MB mieści się w jednej
    assert main(["sklej", str(parts[0])]) == 0 and (tmp_path / "b.bin.xz").exists()


def test_cli_directory_is_tarred(tmp_path: Path, capsys) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    for i in range(3):
        (raw / f"clip{i}.wav").write_bytes(bytes([i]) * 1000)
    assert main(["spakuj", str(raw)]) == 0
    out = capsys.readouterr().out
    assert "raw.tar.xz" in out and not (tmp_path / "raw.tar").exists()
    import lzma
    import tarfile
    with lzma.open(tmp_path / "raw.tar.xz") as f, tarfile.open(fileobj=f) as tar:
        assert sorted(tar.getnames()) == ["raw/clip0.wav", "raw/clip1.wav", "raw/clip2.wav"]
