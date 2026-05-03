from __future__ import annotations

import math


def validate_unit_interval(value: float, name: str) -> float:
    scalar = float(value)
    if not 0.0 <= scalar <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {scalar}")
    return scalar


def schedule_progress(step_idx: int, total_steps: int) -> float:
    if total_steps <= 1:
        return 1.0
    return max(0.0, min(float(step_idx) / float(total_steps - 1), 1.0))


def cosine_schedule(start: float, end: float, progress: float) -> float:
    clipped = max(0.0, min(progress, 1.0))
    eased = 0.5 - 0.5 * math.cos(math.pi * clipped)
    return start + (end - start) * eased


def cosine_gate(
    step_idx: int,
    total_steps: int,
    *,
    start_ratio: float,
    full_ratio: float,
) -> float:
    if full_ratio < start_ratio:
        raise ValueError("full_ratio must be >= start_ratio")
    progress = schedule_progress(step_idx, total_steps)
    if progress <= start_ratio:
        return 0.0
    if progress >= full_ratio:
        return 1.0
    span = max(full_ratio - start_ratio, 1e-6)
    local_progress = (progress - start_ratio) / span
    return cosine_schedule(0.0, 1.0, local_progress)
