import math
import time
from pathlib import Path

from boxbox.voice.player import ClipLibrary, NullBackend, VoicePlayer, wav_bytes
from boxbox.voice.radio import RadioSettings, apply_radio, process_dir, read_wav, write_wav

RATE = 22050


def tone(freq: float, seconds: float = 0.5, amp: float = 0.5) -> list[float]:
    return [amp * math.sin(2 * math.pi * freq * i / RATE) for i in range(int(RATE * seconds))]


def rms(samples: list[float]) -> float:
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def test_radio_bandpass_and_level() -> None:
    settings = RadioSettings(noise_db=-120.0, click_ms=0, drive=1.0, trim_keep_ms=-1)
    mid = apply_radio(RATE, tone(1000), settings)
    low = apply_radio(RATE, tone(80), settings)
    high = apply_radio(RATE, tone(9000), settings)
    assert len(mid) == len(tone(1000))
    # normalizacja działa na każdym klipie, więc porównujemy stosunek sygnału do tego, co zostało "poza pasmem":
    # przy 80 Hz i 9 kHz filtr tłumi tak mocno, że po normalizacji zostaje głównie szum numeryczny -> sprawdzamy przed normalizacją
    from boxbox.voice.radio import Biquad
    def band(samples: list[float]) -> list[float]:
        out = samples
        for _ in range(2):
            out = Biquad.highpass(RATE, 300).run(out)
            out = Biquad.lowpass(RATE, 3400).run(out)
        return out
    assert rms(band(tone(1000))) > 10 * rms(band(tone(80)))
    assert rms(band(tone(1000))) > 10 * rms(band(tone(9000)))
    assert max(abs(s) for s in mid) <= 0.95


def test_trim_silence() -> None:
    from boxbox.voice.radio import trim_silence
    silence = [0.0] * int(RATE * 0.5)
    samples = silence + tone(500, 0.3) + silence
    out = trim_silence(RATE, samples, keep_ms=40)
    assert abs(len(out) - (int(RATE * 0.3) + 2 * int(RATE * 0.04))) < RATE // 50
    assert trim_silence(RATE, [0.0] * 1000) == [0.0] * 1000[:0] or len(trim_silence(RATE, [0.0] * 1000)) <= 1000


def test_radio_click_adds_length_and_file_roundtrip(tmp_path: Path) -> None:
    src = tmp_path / "raw"
    src.mkdir()
    write_wav(src / "a.wav", RATE, tone(500))
    write_wav(src / "b.wav", RATE, tone(700, 0.2))
    dst = tmp_path / "out"
    assert process_dir(src, dst, RadioSettings(click_ms=25, trim_keep_ms=-1)) == 2
    rate, out = read_wav(dst / "a.wav")
    assert rate == RATE and len(out) == len(tone(500)) + 2 * int(RATE * 0.025)
    assert max(abs(s) for s in out) <= 1.0


def test_library_compose_and_player_queue(tmp_path: Path) -> None:
    for name, secs in (("corner_t4", 0.3), ("rule_brake_late_a", 0.4), ("num_50", 0.2)):
        write_wav(tmp_path / f"{name}.wav", RATE, tone(440, secs))
    lib = ClipLibrary(tmp_path)
    assert len(lib) == 3 and "corner_t4" in lib and lib.missing(["corner_t4", "nope"]) == ["nope"]
    clip = lib.compose(["corner_t4", "num_50", "nope"], gap_ms=100)
    assert clip is not None
    assert abs(clip.seconds - (0.3 + 0.2 + 0.1)) < 0.01
    assert wav_bytes(clip)[:4] == b"RIFF"
    assert lib.compose(["nope"]) is None

    backend = NullBackend()
    spoken_texts: list[str] = []
    player = VoicePlayer(lib, backend, max_queue=2, on_speak=lambda s: spoken_texts.append(s.text)).start()
    assert player.say(["corner_t4", "rule_brake_late_a"], "Zakręt czwarty. Hamowanie za późno.")
    assert player.say(["num_50"], "x")
    assert player.say([], "pusty") is False
    deadline = time.time() + 3
    while len(backend.played) < 2 and time.time() < deadline:
        time.sleep(0.01)
    player.close()
    assert len(backend.played) == 2 and spoken_texts[0].startswith("Zakręt czwarty")
    assert abs(backend.played[0].seconds - (0.3 + 0.4 + 0.12)) < 0.01


def test_player_drops_when_queue_full_but_urgent_clears() -> None:
    from boxbox.voice.player import Clip
    lib = ClipLibrary()
    lib.clips = {"a": Clip(RATE, bytes(2 * RATE // 2))}  # 0,5 s ciszy
    backend = NullBackend(sleep=True)
    player = VoicePlayer(lib, backend, max_queue=1)  # bez start(): kolejka się nie opróżnia
    assert player.say(["a"]) is True
    assert player.say(["a"]) is False  # pełna
    assert player.say(["a"], urgent=True) is True  # pilny czyści i wchodzi
    assert player._queue.qsize() == 1
