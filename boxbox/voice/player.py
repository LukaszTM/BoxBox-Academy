"""Odtwarzacz klipów: biblioteka WAV w pamięci, składanie komunikatu, kolejka w osobnym wątku.

Backend na Windows to wbudowany winsound (bez zależności); na Linux/macOS aplay/afplay,
a gdy nic nie ma - NullBackend, który tylko liczy, co by zagrał (testy, serwer).
"""
import io
import platform
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

SILENCE_BETWEEN_CLIPS_MS = 120


@dataclass
class Clip:
    rate: int
    pcm: bytes  # 16-bit mono

    @property
    def seconds(self) -> float:
        return len(self.pcm) / 2 / self.rate


class ClipLibrary:
    def __init__(self, directory: Path | None = None) -> None:
        self.clips: dict[str, Clip] = {}
        self.rate = 22050
        if directory is not None and directory.exists():
            for path in sorted(directory.glob("*.wav")):
                with wave.open(str(path), "rb") as w:
                    if w.getsampwidth() != 2 or w.getnchannels() != 1:
                        continue
                    self.clips[path.stem] = Clip(w.getframerate(), w.readframes(w.getnframes()))
            if self.clips:
                self.rate = next(iter(self.clips.values())).rate

    def __contains__(self, clip_id: str) -> bool:
        return clip_id in self.clips

    def __len__(self) -> int:
        return len(self.clips)

    def missing(self, ids: Sequence[str]) -> list[str]:
        return [i for i in ids if i not in self.clips]

    def compose(self, ids: Sequence[str], gap_ms: int = SILENCE_BETWEEN_CLIPS_MS) -> Clip | None:
        """Skleja klipy z krótką ciszą między nimi; brakujące pomija. None gdy nic nie ma."""
        parts = [self.clips[i].pcm for i in ids if i in self.clips]
        if not parts:
            return None
        gap = bytes(2 * int(self.rate * gap_ms / 1000))
        return Clip(self.rate, gap.join(parts))


def wav_bytes(clip: Clip) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(clip.rate)
        w.writeframes(clip.pcm)
    return buf.getvalue()


class Backend:
    name = "none"

    def play(self, clip: Clip) -> None:  # blokuje do końca klipu
        time.sleep(clip.seconds)

    def stop(self) -> None:
        pass


class WinsoundBackend(Backend):
    """Wbudowany winsound. Z pamięci gra tylko synchronicznie (SND_MEMORY + SND_ASYNC to błąd),
    co nam pasuje: odtwarzacz i tak działa we własnym wątku."""

    name = "winsound"

    def __init__(self) -> None:
        import winsound  # type: ignore[import-not-found]

        self._ws = winsound

    def play(self, clip: Clip) -> None:
        self._ws.PlaySound(wav_bytes(clip), self._ws.SND_MEMORY | self._ws.SND_NODEFAULT)

    def stop(self) -> None:
        self._ws.PlaySound(None, 0)


class CommandBackend(Backend):
    """aplay (Linux) / afplay (macOS): plik tymczasowy, proces blokujący."""

    def __init__(self, command: str) -> None:
        self.command = command
        self.name = command
        self._proc: subprocess.Popen[bytes] | None = None

    def play(self, clip: Clip) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes(clip))
            path = f.name
        try:
            args = [self.command, "-q", path] if self.command == "aplay" else [self.command, path]
            self._proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._proc.wait()
        finally:
            self._proc = None
            Path(path).unlink(missing_ok=True)

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()


class NullBackend(Backend):
    """Nic nie gra; zapisuje, co by zagrał (testy). Czas trwania można pominąć."""

    name = "null"

    def __init__(self, sleep: bool = False) -> None:
        self.played: list[Clip] = []
        self.sleep = sleep

    def play(self, clip: Clip) -> None:
        self.played.append(clip)
        if self.sleep:
            time.sleep(clip.seconds)


def default_backend() -> Backend:
    if platform.system() == "Windows":
        try:
            return WinsoundBackend()
        except ImportError:
            pass
    for cmd in ("aplay", "afplay"):
        if shutil.which(cmd):
            return CommandBackend(cmd)
    return NullBackend(sleep=True)


@dataclass
class Spoken:
    ids: tuple[str, ...]
    text: str = ""


@dataclass
class VoicePlayer:
    """Kolejka komunikatów odtwarzana w tle; `say` nigdy nie blokuje odbioru telemetrii."""

    library: ClipLibrary
    backend: Backend = field(default_factory=default_backend)
    max_queue: int = 3
    on_speak: Callable[[Spoken], None] | None = None  # np. wypisanie tekstu w konsoli
    _queue: "queue.Queue[Spoken | None]" = field(default_factory=queue.Queue, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    spoken: list[Spoken] = field(default_factory=list, init=False)
    errors: list[str] = field(default_factory=list, init=False)

    def start(self) -> "VoicePlayer":
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self

    def say(self, ids: Sequence[str], text: str = "", urgent: bool = False) -> bool:
        """Dodaje komunikat do kolejki. Gdy kolejka pełna, zwykły komunikat przepada (nie nadganiamy)."""
        if not ids:
            return False
        if self._queue.qsize() >= self.max_queue and not urgent:
            return False
        if urgent:
            self.clear()
        self._queue.put(Spoken(tuple(ids), text))
        return True

    def clear(self) -> None:
        with self._lock:
            while True:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
        self.backend.stop()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            clip = self.library.compose(item.ids)
            if clip is None:
                continue
            self.spoken.append(item)
            if self.on_speak:
                try:
                    self.on_speak(item)
                except Exception:  # noqa: BLE001 - wypisywanie nie może zabić wątku głosu
                    pass
            try:
                self.backend.play(clip)
            except Exception as exc:  # noqa: BLE001
                self.errors.append(str(exc))
                print(f"[głos] błąd odtwarzania ({self.backend.name}): {exc}", file=sys.stderr)

    def close(self, timeout: float = 5.0) -> None:
        if self._thread is not None:
            self._queue.put(None)
            self._thread.join(timeout=timeout)
            self._thread = None


def main(argv: Sequence[str] | None = None) -> int:
    """Test głośników: python -m boxbox.voice.player assets/voice misc_hello [kolejne id...]"""
    import argparse

    parser = argparse.ArgumentParser(description="Odtwórz klipy mechanika (test dźwięku)")
    parser.add_argument("voice_dir", type=Path)
    parser.add_argument("ids", nargs="*", default=["misc_hello"])
    args = parser.parse_args(argv)
    library = ClipLibrary(args.voice_dir)
    if len(library) == 0:
        print(f"Brak klipów w {args.voice_dir}")
        return 1
    backend = default_backend()
    missing = library.missing(args.ids)
    if missing:
        print(f"Nie ma klipów: {missing}")
    clip = library.compose(args.ids)
    if clip is None:
        return 1
    print(f"Backend: {backend.name}, klipów w bibliotece: {len(library)}, gram {clip.seconds:.1f} s...")
    try:
        backend.play(clip)
    except Exception as exc:  # noqa: BLE001
        print(f"Błąd odtwarzania: {exc}")
        return 1
    print("Koniec. Jeśli nic nie słychać: sprawdź urządzenie wyjściowe i głośność w mikserze Windows (python.exe).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
