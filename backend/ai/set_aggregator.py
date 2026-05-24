"""
Aggregates per-frame pose metrics across a single working set.
"""

from typing import Any


class SetAggregator:
    """Tracks form flags and angles across frames within one set."""

    def __init__(self) -> None:
        self.reset_set()

    def reset_set(self) -> None:
        """Begin tracking a new set from current rep counter baselines."""
        self.start_rep_count: int = 0
        self.start_good_reps: int = 0
        self.start_bad_reps: int = 0
        self.form_flags_seen: set[str] = set()
        self.angle_samples: list[dict[str, float]] = []

    def begin_set(
        self,
        rep_count: int,
        good_reps: int,
        bad_reps: int,
    ) -> None:
        """Snapshot counters at the start of a set."""
        self.start_rep_count = rep_count
        self.start_good_reps = good_reps
        self.start_bad_reps = bad_reps
        self.form_flags_seen = set()
        self.angle_samples = []

    def record_frame(
        self,
        form_flags: list[str],
        angles: dict[str, float],
    ) -> None:
        """Accumulate data from one processed video frame."""
        for flag in form_flags:
            if flag != "good_rep":
                self.form_flags_seen.add(flag)

        if angles:
            self.angle_samples.append(dict(angles))

    def complete_set(
        self,
        rep_count: int,
        good_reps: int,
        bad_reps: int,
    ) -> dict[str, Any]:
        """
        Compute set summary relative to counters at set start.

        Returns reps_completed, good_reps, bad_reps (this set only),
        form_flags, and avg_angles.
        """
        reps_completed = max(0, rep_count - self.start_rep_count)
        set_good = max(0, good_reps - self.start_good_reps)
        set_bad = max(0, bad_reps - self.start_bad_reps)

        avg_angles: dict[str, float] = {}
        if self.angle_samples:
            keys = self.angle_samples[0].keys()
            for key in keys:
                values = [
                    sample[key]
                    for sample in self.angle_samples
                    if key in sample
                ]
                if values:
                    avg_angles[key] = float(sum(values) / len(values))

        return {
            "reps_completed": reps_completed,
            "good_reps": set_good,
            "bad_reps": set_bad,
            "form_flags": sorted(self.form_flags_seen),
            "avg_angles": avg_angles,
        }
