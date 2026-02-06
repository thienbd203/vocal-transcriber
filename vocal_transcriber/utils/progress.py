"""
Progress tracking utilities.
"""

import time
from typing import Dict, Optional


class ProgressTracker:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.start_time = time.time()
        self.step_start: Optional[float] = None
        self.step_times: Dict[str, float] = {}

    def start_step(self, step_name: str):
        if not self.enabled:
            return
        self.step_start = time.time()
        print(f"\n{'='*60}")
        print(f"🚀 Bắt đầu: {step_name}")
        print(f"{'='*60}")

    def end_step(self, step_name: str):
        if not self.enabled:
            return
        if self.step_start:
            elapsed = time.time() - self.step_start
            self.step_times[step_name] = elapsed
            print(f"\n✅ Hoàn thành: {step_name} ({elapsed:.2f}s)")

    def get_total_elapsed(self) -> float:
        return time.time() - self.start_time

    def estimate_remaining(self, completed_steps: int, total_steps: int) -> str:
        if completed_steps == 0 or not self.step_times:
            return "N/A"
        avg_time = sum(self.step_times.values()) / len(self.step_times)
        remaining_steps = max(0, total_steps - completed_steps)
        return f"{avg_time * remaining_steps:.1f}s"
