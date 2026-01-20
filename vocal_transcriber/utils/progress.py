"""
Progress tracking utilities
"""

import time
from typing import Dict


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
