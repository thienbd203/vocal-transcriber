#!/usr/bin/env python3
"""
CLI interface for STT Service.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from .stt.service import TranscriptionConfig, transcribe_mp3
from .utils.progress import ProgressTracker


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MP3 to Lyrics Chat")
    parser.add_argument("input_mp3", help="Path to input MP3 file")
    parser.add_argument("output_dir", nargs="?", default="./output", help="Output directory")
    parser.add_argument("--language", default="vi", help="Whisper language code")
    parser.add_argument("--model-size", default="medium", help="Whisper model size")
    parser.add_argument("--device", default="auto", help="Device: auto, cpu, cuda, mps")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress output")
    return parser.parse_args()


def _show_startup_spinner(enabled: bool):
    if not enabled:
        return
    spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spinner_idx = 0

    def show_spinner():
        nonlocal spinner_idx
        print(f"\r{spinner_chars[spinner_idx]} Đang khởi động...", end="", flush=True)
        spinner_idx = (spinner_idx + 1) % len(spinner_chars)

    for _ in range(10):
        show_spinner()
        time.sleep(0.1)
    print("\r✅ Ready!           ")


def main():
    """Main CLI function."""
    args = _parse_args()
    _show_startup_spinner(not args.no_progress)

    input_mp3 = Path(args.input_mp3).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not input_mp3.exists():
        raise FileNotFoundError(f"Input file not found: {input_mp3}")

    progress = ProgressTracker(enabled=not args.no_progress)
    total_steps = 3

    print(f"\n{'='*60}")
    print("🎵 STT SERVICE - MP3 to Lyrics Chat")
    print(f"{'='*60}")
    print(f"📥 Input: {input_mp3.name}")
    print(f"📤 Output: {output_dir}")
    print(f"⏱️  Started: {time.strftime('%H:%M:%S')}")
    print(f"{'='*60}")

    try:
        print(f"\n📊 Step 1/{total_steps}: Tách vocal khỏi nhạc")
        print(f"\n📊 Step 2/{total_steps}: Chuyển đổi giọng nói thành text")
        print(f"\n📊 Step 3/{total_steps}: Định dạng lyrics chat")

        config = TranscriptionConfig(
            language=args.language,
            model_size=args.model_size,
            device=args.device,
        )

        lyrics_chat = transcribe_mp3(
            input_mp3=input_mp3,
            output_dir=output_dir,
            config=config,
            progress=progress,
        )

        output_json = output_dir / "lyrics.json"
        with output_json.open("w", encoding="utf-8") as f:
            json.dump(lyrics_chat, f, ensure_ascii=False, indent=2)

        total_elapsed = progress.get_total_elapsed()
        print(f"\n{'='*60}")
        print("🎉 HOÀN TẤT TẤT CẢ CÁC BƯỚC!")
        print(f"{'='*60}")
        print(f"📁 Output file: {output_json}")
        print("📊 Statistics:")
        print(f"   • Total segments: {len(lyrics_chat['segments'])}")
        print(f"   • Duration: {lyrics_chat['duration']}s")
        print(f"   • Language: {lyrics_chat['language']}")
        print("\n⏱️  Time Summary:")
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
