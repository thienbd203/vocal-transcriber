"""
STT Service - Core functionality for vocal separation and transcription
"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

import torch
import whisper
from tqdm import tqdm

from ..utils.progress import ProgressTracker


def detect_device() -> str:
    """Detect available device for processing"""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def separate_vocals(input_mp3: Path, output_dir: Path, progress: ProgressTracker) -> Path:
    """Separate vocals from music using Demucs"""
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

    # Progress bar for Demucs
    with tqdm(total=100, desc="🎵 Đang xử lý", unit="%", 
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        
        # Simulate progress based on typical Demucs processing time
        start_time = time.time()
        while process.poll() is None:
            elapsed = time.time() - start_time
            simulated_progress = min(90, int((elapsed / 60) * 90))
            if simulated_progress > pbar.n:
                pbar.update(simulated_progress - pbar.n)
            time.sleep(0.5)
        
        pbar.update(100 - pbar.n)
        
        if process.returncode != 0:
            output = process.stdout.read()
            print(output)
            raise RuntimeError("Demucs failed")

    vocal_path = (
        output_dir
        / "htdemucs"
        / input_mp3.stem
        / "vocals.wav"
    )

    if not vocal_path.exists():
        raise RuntimeError("Vocal file not found after Demucs processing")

    final_vocal = output_dir / "vocals.wav"
    shutil.move(vocal_path, final_vocal)

    progress.end_step("Tách vocal khỏi nhạc (Demucs)")
    return final_vocal


def transcribe_vocals(
    vocal_wav: Path,
    language: str = "vi",
    model_size: str = "medium",
    progress: ProgressTracker = None,
) -> Dict[str, Any]:
    """Transcribe vocals using Whisper"""
    progress.start_step("Chuyển đổi giọng nói thành text (Whisper)")
    
    device = detect_device()
    print(f"🧠 Loading Whisper model [{model_size}] on {device}")
    
    # Progress bar for loading model
    with tqdm(total=100, desc="📥 Loading model", unit="%",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        model = whisper.load_model(model_size, device="cpu")
        pbar.update(100)

    print("📝 Transcribing vocals...")
    
    # Progress bar for transcription
    with tqdm(total=100, desc="🎤 Đang transcribe", unit="%",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
        result = model.transcribe(
            str(vocal_wav),
            language=language,
            fp16=False,
            temperature=0.0,
        )
        pbar.update(100)

    progress.end_step("Chuyển đổi giọng nói thành text (Whisper)")
    return result


def format_lyrics_chat(result: Dict[str, Any], progress: ProgressTracker = None) -> Dict[str, Any]:
    """Format transcription result to lyrics chat JSON"""
    progress.start_step("Định dạng lyrics chat JSON")
    
    segments: List[Dict[str, Any]] = []
    total_segments = len(result.get("segments", []))
    
    # Progress bar for formatting
    with tqdm(total=total_segments, desc="📝 Formatting", unit="segments",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        for seg in result.get("segments", []):
            text = seg["text"].strip()
            if not text:
                pbar.update(1)
                continue

            # Split text by commas and create separate segments
            parts = [part.strip() for part in text.split(",") if part.strip()]
            
            if len(parts) > 1:
                # If multiple parts after splitting, distribute time evenly
                duration = seg["end"] - seg["start"]
                part_duration = duration / len(parts)
                
                for i, part in enumerate(parts):
                    start_time = seg["start"] + (i * part_duration)
                    end_time = start_time + part_duration
                    
                    segments.append(
                        {
                            "start": round(float(start_time), 2),
                            "end": round(float(end_time), 2),
                            "text": part,
                        }
                    )
            else:
                # If no comma or only one part, keep original
                segments.append(
                    {
                        "start": round(float(seg["start"]), 2),
                        "end": round(float(seg["end"]), 2),
                        "text": text,
                    }
                )
            
            pbar.update(1)

    progress.end_step("Định dạng lyrics chat JSON")
    
    return {
        "language": result.get("language", "unknown"),
        "duration": round(float(result.get("duration", 0)), 2),
        "segments": segments,
    }
