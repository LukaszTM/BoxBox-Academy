import pytest

from boxbox.telemetry.header import HEADER_SIZE, PacketHeader, PacketId, pack_header, parse_header


def make_header(packet_id: int = 6) -> PacketHeader:
    return PacketHeader(2025, 25, 1, 2, 1, packet_id, 2**63 + 5, 12.5, 100, 200, 7, 255)


def test_header_size_is_29() -> None:
    assert HEADER_SIZE == 29


def test_parse_roundtrip_ignores_payload() -> None:
    header = make_header()
    assert parse_header(pack_header(header) + b"\x00" * 100) == header


def test_kind() -> None:
    assert make_header(6).kind is PacketId.CAR_TELEMETRY
    assert make_header(200).kind is None


def test_short_packet_rejected() -> None:
    with pytest.raises(ValueError):
        parse_header(b"\x00" * 28)
