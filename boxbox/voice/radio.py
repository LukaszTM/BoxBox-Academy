"""Efekt radia na klipach WAV (16-bit mono): pasmo 300-3400 Hz, kompresja, lekki szum, klik PTT.

Czysty Python (array + dwa filtry biquad), bo klipy przetwarzamy raz, nie w grze.
Użycie: python -m boxbox.voice.radio assets/voice/raw assets/voice
"""
import argparse
import math
import random
import wave
from array import array
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Biquad:
    """Filtr 2. rzędu (RBJ cookbook), postać bezpośrednia I."""

    b0: float
    b1: float
    b2: float
    a1: float
    a2: float

    @classmethod
    def highpass(cls, rate: int, freq: float, q: float = 0.707) -> "Biquad":
        w0 = 2 * math.pi * freq / rate
        alpha = math.sin(w0) / (2 * q)
        c = math.cos(w0)
        a0 = 1 + alpha
        return cls((1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0, -2 * c / a0, (1 - alpha) / a0)

    @classmethod
    def lowpass(cls, rate: int, freq: float, q: float = 0.707) -> "Biquad":
        w0 = 2 * math.pi * freq / rate
        alpha = math.sin(w0) / (2 * q)
        c = math.cos(w0)
        a0 = 1 + alpha
        return cls((1 - c) / 2 / a0, (1 - c) / a0, (1 - c) / 2 / a0, -2 * c / a0, (1 - alpha) / a0)

    def run(self, samples: list[float]) -> list[float]:
        x1 = x2 = y1 = y2 = 0.0
        out = []
        b0, b1, b2, a1, a2 = self.b0, self.b1, self.b2, self.a1, self.a2
        for x in samples:
            y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1, y2, y1 = x1, x, y1, y
            out.append(y)
        return out


@dataclass(frozen=True)
class RadioSettings:
    low_hz: float = 300.0
    high_hz: float = 3400.0
    drive: float = 3.0  # wzmocnienie przed miękkim ograniczeniem (kompresja "radiowa")
    noise_db: float = -48.0  # szum tła
    click_ms: int = 25  # klik PTT na początku i końcu (0 = bez)
    click_db: float = -18.0
    peak: float = 0.9  # normalizacja szczytu


def read_wav(path: Path) -> tuple[int, list[float]]:
    with wave.open(str(path), "rb") as w:
        assert w.getsampwidth() == 2, "oczekiwany WAV 16-bit"
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
        data = array("h", frames)
        if w.getnchannels() == 2:
            data = array("h", data[0::2])  # lewy kanał
    return rate, [s / 32768.0 for s in data]


def write_wav(path: Path, rate: int, samples: Sequence[float]) -> None:
    data = array("h", (int(max(-1.0, min(1.0, s)) * 32767) for s in samples))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def _soft_clip(x: float) -> float:
    return math.tanh(x)


def apply_radio(rate: int, samples: list[float], settings: RadioSettings = RadioSettings(), seed: int = 7) -> list[float]:
    # pasmo: 2x high-pass + 2x low-pass (stromsze zbocza)
    out = samples
    for _ in range(2):
        out = Biquad.highpass(rate, settings.low_hz).run(out)
        out = Biquad.lowpass(rate, settings.high_hz).run(out)
    # kompresja: wzmocnienie + miękkie ograniczenie
    out = [_soft_clip(s * settings.drive) for s in out]
    # normalizacja
    peak = max((abs(s) for s in out), default=0.0) or 1.0
    gain = settings.peak / peak
    out = [s * gain for s in out]
    # szum tła
    rng = random.Random(seed)
    noise_amp = 10 ** (settings.noise_db / 20)
    out = [s + rng.uniform(-noise_amp, noise_amp) for s in out]
    # klik PTT: krótki impuls szumu na początku i końcu
    if settings.click_ms > 0:
        n = int(rate * settings.click_ms / 1000)
        click_amp = 10 ** (settings.click_db / 20)
        click = [rng.uniform(-click_amp, click_amp) * (1 - i / n) for i in range(n)]
        out = click + out + list(reversed(click))
    return out


def process_dir(src: Path, dst: Path, settings: RadioSettings = RadioSettings()) -> int:
    count = 0
    for path in sorted(src.glob("*.wav")):
        rate, samples = read_wav(path)
        write_wav(dst / path.name, rate, apply_radio(rate, samples, settings))
        count += 1
    return count


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Efekt radia na klipach WAV")
    parser.add_argument("src", type=Path, help="folder z surowymi klipami")
    parser.add_argument("dst", type=Path, help="folder docelowy")
    parser.add_argument("--drive", type=float, default=RadioSettings.drive)
    parser.add_argument("--noise-db", type=float, default=RadioSettings.noise_db)
    parser.add_argument("--no-click", action="store_true")
    args = parser.parse_args(argv)
    settings = RadioSettings(drive=args.drive, noise_db=args.noise_db, click_ms=0 if args.no_click else RadioSettings.click_ms)
    n = process_dir(args.src, args.dst, settings)
    print(f"przetworzono {n} klipów -> {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
