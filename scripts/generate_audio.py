"""Generate English audio (Piper TTS) and sound effects for scene.json.

Run with the backend venv's Python, since piper-tts is installed there:
    backend/venv/Scripts/python.exe scripts/generate_audio.py [--force]

Writes into frontend/public/scene/audio/ and frontend/public/scene/sfx/.
Skips files that already exist unless --force is given.
"""

import argparse
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENE_PATH = ROOT / "frontend" / "public" / "scene" / "scene.json"
AUDIO_DIR = ROOT / "frontend" / "public" / "scene" / "audio"
SFX_DIR = ROOT / "frontend" / "public" / "scene" / "sfx"
VOICES_DIR = ROOT / "scripts" / "voices"

VOICE_MODEL = VOICES_DIR / "en_US-lessac-medium.onnx"
VOICE_CONFIG = VOICES_DIR / "en_US-lessac-medium.onnx.json"

SLOW_LENGTH_SCALE = 1.4
SAMPLE_RATE = 22050


def find_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidates = list(Path(local_app_data).glob("Microsoft/WinGet/Packages/*FFmpeg*/**/ffmpeg.exe"))
        if candidates:
            return str(candidates[0])
    raise RuntimeError(
        "ffmpeg not found on PATH. Install it (e.g. `winget install Gyan.FFmpeg`) "
        "and make sure it's reachable."
    )


def check_voice() -> None:
    if not VOICE_MODEL.exists() or not VOICE_CONFIG.exists():
        raise RuntimeError(
            f"Piper voice not found at {VOICE_MODEL}.\n"
            "Download it first:\n"
            f"  python -m piper.download_voices en_US-lessac-medium --download-dir {VOICES_DIR}"
        )


def synth_wav(text: str, out_wav: Path, length_scale: float | None) -> None:
    cmd = [
        sys.executable, "-m", "piper",
        "-m", str(VOICE_MODEL),
        "-c", str(VOICE_CONFIG),
        "-f", str(out_wav),
    ]
    if length_scale is not None:
        cmd += ["--length-scale", str(length_scale)]
    result = subprocess.run(cmd, input=text, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"piper failed for text {text!r}:\n{result.stderr}")


def wav_to_mp3(wav_path: Path, mp3_path: Path, ffmpeg_exe: str) -> None:
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_exe, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-qscale:a", "4", str(mp3_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed converting {wav_path} -> {mp3_path}:\n{result.stderr}")


def synth_to_mp3(text: str, mp3_path: Path, length_scale: float | None, ffmpeg_exe: str) -> None:
    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "out.wav"
        synth_wav(text, wav_path, length_scale)
        wav_to_mp3(wav_path, mp3_path, ffmpeg_exe)


def write_tone_wav(path: Path, segments: list[tuple[float, float, float]]) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for freq, dur, amp in segments:
            n = int(SAMPLE_RATE * dur)
            fade = max(1, int(n * 0.1))
            for i in range(n):
                t = i / SAMPLE_RATE
                env = 1.0
                if i < fade:
                    env = i / fade
                elif i > n - fade:
                    env = (n - i) / fade
                sample = amp * env * math.sin(2 * math.pi * freq * t)
                frames += struct.pack("<h", int(sample * 32767))
        wf.writeframes(bytes(frames))


def tone_to_mp3(segments: list[tuple[float, float, float]], mp3_path: Path, ffmpeg_exe: str) -> None:
    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "tone.wav"
        write_tone_wav(wav_path, segments)
        wav_to_mp3(wav_path, mp3_path, ffmpeg_exe)


def collect_lines(scene: dict) -> dict[str, str]:
    lines: dict[str, str] = {}
    for turn in scene["turns"]:
        lines[turn["line"]["id"]] = turn["line"]["text"]
        for reply in turn["say"]["replies"]:
            lines[reply["id"]] = reply["text"]
    repeat = scene["repeatRequest"]
    lines[repeat["id"]] = repeat["text"]
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Regenerate files even if they already exist")
    args = parser.parse_args()

    ffmpeg_exe = find_ffmpeg()
    check_voice()

    scene = json.loads(SCENE_PATH.read_text(encoding="utf-8"))
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    SFX_DIR.mkdir(parents=True, exist_ok=True)

    tasks: list[tuple[Path, "object"]] = []

    for line_id, text in collect_lines(scene).items():
        normal_path = AUDIO_DIR / f"{line_id}.mp3"
        slow_path = AUDIO_DIR / f"{line_id}_slow.mp3"
        tasks.append((normal_path, (synth_to_mp3, text, normal_path, None, ffmpeg_exe)))
        tasks.append((slow_path, (synth_to_mp3, text, slow_path, SLOW_LENGTH_SCALE, ffmpeg_exe)))

    for idx, turn in enumerate(scene["turns"], start=1):
        help_path = AUDIO_DIR / f"help_{turn['id']}.mp3"
        help_text = f"Placeholder. Rohingya help for turn {idx} goes here."
        tasks.append((help_path, (synth_to_mp3, help_text, help_path, None, ffmpeg_exe)))

    correct_path = SFX_DIR / "correct.mp3"
    tasks.append((correct_path, (tone_to_mp3, [(660.0, 0.12, 0.5), (880.0, 0.18, 0.5)], correct_path, ffmpeg_exe)))

    retry_path = SFX_DIR / "retry.mp3"
    tasks.append((retry_path, (tone_to_mp3, [(220.0, 0.35, 0.35)], retry_path, ffmpeg_exe)))

    created: list[Path] = []
    skipped: list[Path] = []

    for path, job in tasks:
        if path.exists() and not args.force:
            skipped.append(path)
            continue
        fn, *fn_args = job
        fn(*fn_args)
        created.append(path)

    print(f"Created {len(created)} file(s):")
    for p in created:
        print(f"  {p.relative_to(ROOT)}")
    print(f"Skipped {len(skipped)} file(s) that already existed (use --force to regenerate):")
    for p in skipped:
        print(f"  {p.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
