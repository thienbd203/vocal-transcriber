"""
STT Service - Core functionality for vocal separation and transcription.
"""

import logging
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Any, Optional

import torch
import whisper
from tqdm import tqdm

from ..utils.progress import ProgressTracker

logger = logging.getLogger(__name__)

VALID_DEVICES = {"cpu", "cuda", "mps", "auto"}


@dataclass(frozen=True)
class TranscriptionConfig:
    language: str = "vi"
    model_size: str = "medium"
    device: str = "auto"
    fp16: Optional[bool] = None


def detect_device() -> str:
    """Detect available device for processing."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def resolve_device(device: Optional[str]) -> str:
    """Normalize device selection."""
    if not device or device == "auto":
        return detect_device()
    device = device.lower()
    if device not in VALID_DEVICES:
        raise ValueError(f"Unsupported device: {device}")
    return device


def _progress_enabled(progress: Optional[ProgressTracker]) -> bool:
    return bool(progress and progress.enabled)


def _new_pbar(total: int, desc: str, unit: str, enabled: bool):
    return tqdm(
        total=total,
        desc=desc,
        unit=unit,
        disable=not enabled,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    )


@lru_cache(maxsize=4)
def _load_whisper_model(model_size: str, device: str):
    return whisper.load_model(model_size, device=device)


def _find_vocal_path(output_dir: Path, input_stem: str) -> Path:
    candidates = list(output_dir.rglob("vocals.wav"))
    if not candidates:
        raise RuntimeError("Vocal file not found after Demucs processing")

    preferred = [p for p in candidates if input_stem in p.parts]
    pool = preferred or candidates
    pool.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return pool[0]


def separate_vocals(input_mp3: Path, output_dir: Path, progress: Optional[ProgressTracker]) -> Path:
    """Separate vocals from music using Demucs."""
    if not input_mp3.exists():
        raise FileNotFoundError(f"Input file not found: {input_mp3}")

    if progress:
        progress.start_step("Tách vocal khỏi nhạc (Demucs)")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems",
        "vocals",
        "-o",
        str(output_dir),
        str(input_mp3),
    ]

    enabled = _progress_enabled(progress)
    with _new_pbar(100, "🎵 Đang xử lý", "%", enabled) as pbar:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            text=True,
        )

        start_time = time.time()
        while process.poll() is None:
            elapsed = time.time() - start_time
            simulated = min(90, int((elapsed / 60) * 90))
            if simulated > pbar.n:
                pbar.update(simulated - pbar.n)
            time.sleep(0.5)

        pbar.update(100 - pbar.n)

        if process.returncode != 0:
            raise RuntimeError("Demucs failed. Ensure Demucs is installed and the input is valid.")

    vocal_path = _find_vocal_path(output_dir, input_mp3.stem)
    final_vocal = output_dir / "vocals.wav"
    if final_vocal.exists():
        final_vocal.unlink()
    shutil.move(str(vocal_path), str(final_vocal))

    if progress:
        progress.end_step("Tách vocal khỏi nhạc (Demucs)")
    return final_vocal


def transcribe_vocals(
    vocal_wav: Path,
    config: Optional[TranscriptionConfig] = None,
    progress: Optional[ProgressTracker] = None,
) -> Dict[str, Any]:
    """Transcribe vocals using Whisper."""
    config = config or TranscriptionConfig()
    if progress:
        progress.start_step("Chuyển đổi giọng nói thành text (Whisper)")

    device = resolve_device(config.device)
    fp16 = config.fp16 if config.fp16 is not None else device == "cuda"

    if _progress_enabled(progress):
        print(f"🧠 Loading Whisper model [{config.model_size}] on {device}")

    with _new_pbar(100, "📥 Loading model", "%", _progress_enabled(progress)) as pbar:
        model = _load_whisper_model(config.model_size, device)
        pbar.update(100)

    if _progress_enabled(progress):
        print("📝 Transcribing vocals...")

    with _new_pbar(100, "🎤 Đang transcribe", "%", _progress_enabled(progress)) as pbar:
        result = model.transcribe(
            str(vocal_wav),
            language=config.language,
            fp16=fp16,
            temperature=0.0,
        )
        pbar.update(100)

    if progress:
        progress.end_step("Chuyển đổi giọng nói thành text (Whisper)")
    return result


def format_lyrics_chat(
    result: Dict[str, Any],
    progress: Optional[ProgressTracker] = None,
) -> Dict[str, Any]:
    """Format transcription result to lyrics chat JSON."""
    if progress:
        progress.start_step("Định dạng lyrics chat JSON")

    segments: List[Dict[str, Any]] = []
    total_segments = len(result.get("segments", []))

    with _new_pbar(total_segments, "📝 Formatting", "segments", _progress_enabled(progress)) as pbar:
        for seg in result.get("segments", []):
            text = str(seg.get("text", "")).strip()
            if not text:
                pbar.update(1)
                continue

            parts = [part.strip() for part in text.split(",") if part.strip()]

            if len(parts) > 1:
                duration = float(seg["end"]) - float(seg["start"])
                part_duration = duration / len(parts)

                for i, part in enumerate(parts):
                    start_time = float(seg["start"]) + (i * part_duration)
                    end_time = start_time + part_duration
                    segments.append(
                        {
                            "start": round(start_time, 2),
                            "end": round(end_time, 2),
                            "text": part,
                        }
                    )
            else:
                segments.append(
                    {
                        "start": round(float(seg["start"]), 2),
                        "end": round(float(seg["end"]), 2),
                        "text": text,
                    }
                )

            pbar.update(1)

    if progress:
        progress.end_step("Định dạng lyrics chat JSON")

    return {
        "language": result.get("language", "unknown"),
        "duration": round(float(result.get("duration", 0)), 2),
        "segments": segments,
    }


def transcribe_mp3(
    input_mp3: Path,
    output_dir: Path,
    config: Optional[TranscriptionConfig] = None,
    progress: Optional[ProgressTracker] = None,
) -> Dict[str, Any]:
    """Full pipeline: separate vocals -> transcribe -> format."""
    config = config or TranscriptionConfig()
    vocal_wav = separate_vocals(input_mp3, output_dir, progress)
    whisper_result = transcribe_vocals(vocal_wav=vocal_wav, config=config, progress=progress)
    return format_lyrics_chat(whisper_result, progress)
