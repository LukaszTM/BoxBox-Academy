"""Generuje klipy WAV z katalogu fraz przez API ElevenLabs (jednorazowo, bez zależności).

Użycie (Windows, w folderze projektu):
  set ELEVENLABS_API_KEY=...        (klucz z ustawień konta; nie wpisuj go do plików)
  set ELEVENLABS_VOICE_ID=...       (id głosu, np. "Piotr - Neutral and Mature": zakładka Voices -> ID)
  py -3 tools\\generate_voice_elevenlabs.py assets\\voice\\phrases.csv assets\\voice\\raw

Pomija klipy, które już istnieją, więc można uruchamiać wiele razy (limit znaków na planie free).
Ustawienia głosu z próbki: stability 0.36, similarity 0.68, speed 1.0 (nazwa pliku próbki: s36 sb68 sp100).
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

API = "https://api.elevenlabs.io/v1/text-to-speech"
SAMPLE_RATE = 22050
MODEL = "eleven_multilingual_v2"


def synthesize(text: str, voice_id: str, api_key: str, stability: float, similarity: float, speed: float) -> bytes:
    body = json.dumps({
        "text": text,
        "model_id": MODEL,
        "voice_settings": {"stability": stability, "similarity_boost": similarity, "speed": speed},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API}/{voice_id}?output_format=pcm_{SAMPLE_RATE}",
        data=body, method="POST",
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/pcm"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def save_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--stability", type=float, default=0.36)
    parser.add_argument("--similarity", type=float, default=0.68)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--only", nargs="*", help="tylko te id (np. do poprawek)")
    parser.add_argument("--dry-run", action="store_true", help="policz znaki, nic nie wysyłaj")
    parser.add_argument("--done-dir", type=Path, help="pomiń też klipy, które są już w tym folderze (np. assets/voice po efekcie radia)")
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
    with open(args.csv, newline="", encoding="utf-8") as f:
        rows = [(r["id"], r["text"]) for r in csv.DictReader(f)]
    if args.only:
        rows = [r for r in rows if r[0] in set(args.only)]
    args.out.mkdir(parents=True, exist_ok=True)
    def exists(key: str) -> bool:
        return (args.out / f"{key}.wav").exists() or (args.done_dir is not None and (args.done_dir / f"{key}.wav").exists())

    todo = [(k, t) for k, t in rows if not exists(k)]
    chars = sum(len(t) for _, t in todo)
    print(f"{len(rows)} fraz w katalogu, {len(todo)} do wygenerowania, {chars} znaków")
    if args.dry_run:
        return 0
    if not api_key or not voice_id:
        print("Ustaw zmienne ELEVENLABS_API_KEY i ELEVENLABS_VOICE_ID.", file=sys.stderr)
        return 1
    for i, (key, text) in enumerate(todo, 1):
        for attempt in range(3):
            try:
                pcm = synthesize(text, voice_id, api_key, args.stability, args.similarity, args.speed)
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:200]
                if exc.code == 429 and attempt < 2:
                    time.sleep(5)
                    continue
                print(f"[{key}] błąd HTTP {exc.code}: {detail}", file=sys.stderr)
                return 1
        save_wav(args.out / f"{key}.wav", pcm)
        print(f"[{i}/{len(todo)}] {key}: {text}")
        time.sleep(0.3)  # łagodnie dla limitu zapytań
    print(f"Gotowe: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
