#!/usr/bin/env python3
"""
STT Service
MP3 -> (Demucs vocal separation) -> Whisper transcription -> Lyrics Chat JSON
"""

import json
import subprocess
import sys
import shutil
import time
from pathlib import Path
from typing import List, Dict, Any

import whisper
import torch
from tqdm import tqdm


# -----------------------------
# Utils
# -----------------------------
class ProgressTracker:
    def __init__(self):
        self.start_time = time.time()
        self.step_start = None
        self.step_times = {}
    
    def start_step(self, step_name: str):
        self.step_start = time.time()
        print(f"\n{'='*60}")
        print(f"🚀 Bắt đầu: {step_name}")
        print(f"{'='*60}")
    
    def end_step(self, step_name: str):
        if self.step_start:
            elapsed = time.time() - self.step_start
            self.step_times[step_name] = elapsed
            print(f"\n✅ Hoàn thành: {step_name} ({elapsed:.2f}s)")
    
    def get_total_elapsed(self):
        return time.time() - self.start_time
    
    def estimate_remaining(self, completed_steps: int, total_steps: int):
        if completed_steps == 0:
            return "N/A"
        avg_time = sum(self.step_times.values()) / len(self.step_times)
        remaining_steps = total_steps - completed_steps
        return f"{avg_time * remaining_steps:.1f}s"


def detect_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def run_command(cmd: List[str]) -> None:
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if process.returncode != 0:
        print(process.stdout)
        raise RuntimeError("Command failed")


# -----------------------------
# Step 1: Separate vocals
# -----------------------------
def separate_vocals(input_mp3: Path, output_dir: Path, progress: ProgressTracker) -> Path:
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

    # Tạo progress bar cho Demucs
    with tqdm(total=100, desc="🎵 Đang xử lý", unit="%", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
        # Chạy Demucs với progress animation
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
            # Demucs thường mất khoảng 1-2 phút, simulate progress tương ứng
            simulated_progress = min(90, int((elapsed / 60) * 90))  # 90% trong 60 giây đầu
            if simulated_progress > pbar.n:
                pbar.update(simulated_progress - pbar.n)
            time.sleep(0.5)
        
        # Hoàn thành
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


# -----------------------------
# Step 2: Whisper transcription
# -----------------------------
def transcribe_vocals(
    vocal_wav: Path,
    language: str = "vi",
    model_size: str = "medium",
    progress: ProgressTracker = None,
) -> Dict[str, Any]:
    progress.start_step("Chuyển đổi giọng nói thành text (Whisper)")
    
    device = detect_device()
    print(f"🧠 Loading Whisper model [{model_size}] on {device}")
    
    # Progress bar cho loading model
    with tqdm(total=100, desc="📥 Loading model", unit="%", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        model = whisper.load_model(model_size, device="cpu")
        pbar.update(100)

    print("📝 Transcribing vocals...")
    
    # Tạo progress bar cho transcription
    with tqdm(total=100, desc="🎤 Đang transcribe", unit="%", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
        # Whisper không có callback progress, nên chúng ta simulate
        result = model.transcribe(
            str(vocal_wav),
            language=language,
            fp16=False,
            temperature=0.0,
        )
        pbar.update(100)

    progress.end_step("Chuyển đổi giọng nói thành text (Whisper)")
    return result


# -----------------------------
# Step 3: Format to lyrics chat JSON
# -----------------------------
def format_lyrics_chat(result: Dict[str, Any], progress: ProgressTracker = None) -> Dict[str, Any]:
    progress.start_step("Định dạng lyrics chat JSON")
    
    segments: List[Dict[str, Any]] = []
    total_segments = len(result.get("segments", []))
    
    # Progress bar cho formatting
    with tqdm(total=total_segments, desc="📝 Formatting", unit="segments", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        for seg in result.get("segments", []):
            text = seg["text"].strip()
            if not text:
                pbar.update(1)
                continue

            # Tách text theo dấu phẩy và tạo các segment riêng biệt
            parts = [part.strip() for part in text.split(",") if part.strip()]
            
            if len(parts) > 1:
                # Nếu có nhiều phần sau khi tách, phân chia thời gian đều
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
                # Nếu không có dấu phẩy hoặc chỉ có một phần, giữ nguyên
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


# -----------------------------
# Main
# -----------------------------
def main():
    # Spinner animation
    spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spinner_idx = 0
    
    def show_spinner():
        nonlocal spinner_idx
        print(f"\r{spinner_chars[spinner_idx]} Đang khởi động...", end='', flush=True)
        spinner_idx = (spinner_idx + 1) % len(spinner_chars)
    
    # Hiển thị spinner khi khởi động
    for _ in range(10):
        show_spinner()
        time.sleep(0.1)
    print("\r✅ Ready!           ")
    
    if len(sys.argv) < 2:
        print("Usage: python main.py <input.mp3> [output_dir]")
        sys.exit(1)

    input_mp3 = Path(sys.argv[1]).expanduser().resolve()
    output_dir = (
        Path(sys.argv[2]).expanduser().resolve()
        if len(sys.argv) >= 3
        else Path("./output").resolve()
    )

    if not input_mp3.exists():
        raise FileNotFoundError(f"Input file not found: {input_mp3}")

    # Khởi tạo progress tracker
    progress = ProgressTracker()
    total_steps = 3
    
    # Header
    print(f"\n{'='*60}")
    print(f"🎵 STT SERVICE - MP3 to Lyrics Chat")
    print(f"{'='*60}")
    print(f"📥 Input: {input_mp3.name}")
    print(f"📤 Output: {output_dir}")
    print(f"⏱️  Started: {time.strftime('%H:%M:%S')}")
    print(f"{'='*60}")

    try:
        # Step 1: Separate vocals
        print(f"\n📊 Step 1/{total_steps}: Tách vocal khỏi nhạc")
        vocal_wav = separate_vocals(input_mp3, output_dir, progress)
        
        # Step 2: Transcribe
        print(f"\n📊 Step 2/{total_steps}: Chuyển đổi giọng nói thành text")
        print(f"⏳ Estimated remaining: {progress.estimate_remaining(1, total_steps)}")
        whisper_result = transcribe_vocals(
            vocal_wav=vocal_wav,
            language="vi",
            model_size="medium",
            progress=progress,
        )
        
        # Step 3: Format
        print(f"\n📊 Step 3/{total_steps}: Định dạng lyrics chat")
        print(f"⏳ Estimated remaining: {progress.estimate_remaining(2, total_steps)}")
        lyrics_chat = format_lyrics_chat(whisper_result, progress)
        
        # Save output
        output_json = output_dir / "lyrics.json"
        with output_json.open("w", encoding="utf-8") as f:
            json.dump(lyrics_chat, f, ensure_ascii=False, indent=2)
        
        # Summary
        total_elapsed = progress.get_total_elapsed()
        print(f"\n{'='*60}")
        print(f"🎉 HOÀN TẤT TẤT CẢ CÁC BƯỚC!")
        print(f"{'='*60}")
        print(f"📁 Output file: {output_json}")
        print(f"📊 Statistics:")
        print(f"   • Total segments: {len(lyrics_chat['segments'])}")
        print(f"   • Duration: {lyrics_chat['duration']}s")
        print(f"   • Language: {lyrics_chat['language']}")
        print(f"\n⏱️  Time Summary:")
        for step, duration in progress.step_times.items():
            print(f"   • {step}: {duration:.2f}s")
        print(f"   • Total time: {total_elapsed:.2f}s")
        print(f"\n✨ Success! Lyrics saved to: {output_json}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()