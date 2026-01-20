#!/usr/bin/env python3
"""
CLI interface for STT Service
"""

import json
import sys
import time
from pathlib import Path

from ..stt.service import separate_vocals, transcribe_vocals, format_lyrics_chat
from ..utils.progress import ProgressTracker


def main():
    """Main CLI function"""
    # Spinner animation
    spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spinner_idx = 0
    
    def show_spinner():
        nonlocal spinner_idx
        print(f"\r{spinner_chars[spinner_idx]} Đang khởi động...", end='', flush=True)
        spinner_idx = (spinner_idx + 1) % len(spinner_chars)
    
    # Show spinner on startup
    for _ in range(10):
        show_spinner()
        time.sleep(0.1)
    print("\r✅ Ready!           ")
    
    if len(sys.argv) < 2:
        print("Usage: python -m vocal_transcriber.cli <input.mp3> [output_dir]")
        sys.exit(1)

    input_mp3 = Path(sys.argv[1]).expanduser().resolve()
    output_dir = (
        Path(sys.argv[2]).expanduser().resolve()
        if len(sys.argv) >= 3
        else Path("./output").resolve()
    )

    if not input_mp3.exists():
        raise FileNotFoundError(f"Input file not found: {input_mp3}")

    # Initialize progress tracker
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
