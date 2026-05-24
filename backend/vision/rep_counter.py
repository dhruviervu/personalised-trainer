"""
Rep counter facade that delegates to the active exercise implementation.
"""

from typing import Any

from vision.exercises.base_exercise import BaseExercise


class RepCounter:
    """Tracks reps and form feedback via a pluggable exercise state machine."""

    def __init__(self) -> None:
        self._exercise: BaseExercise | None = None
        self.total_reps: int = 0
        self.good_reps: int = 0
        self.bad_reps: int = 0
        self.set_start_reps: int = 0
        self.set_start_good: int = 0
        self.set_start_bad: int = 0
        self.current_set_good: int = 0
        self.current_set_bad: int = 0

    def set_exercise(self, exercise: BaseExercise) -> None:
        """Set the active exercise and reset aggregate counters."""
        self._exercise = exercise
        self.total_reps = 0
        self.good_reps = 0
        self.bad_reps = 0
        self.set_start_reps = 0
        self.set_start_good = 0
        self.set_start_bad = 0
        self.current_set_good = 0
        self.current_set_bad = 0

    def reset_set(self) -> None:
        """Start a new set while preserving session totals."""
        self.set_start_reps = self.total_reps
        self.set_start_good = self.good_reps
        self.set_start_bad = self.bad_reps
        self.current_set_good = 0
        self.current_set_bad = 0

    def process(
        self,
        landmarks: list[dict[str, Any]],
        angles: dict[str, float],
    ) -> dict[str, Any]:
        """
        Run one frame through the active exercise.

        Returns rep_count, good_reps, bad_reps, phase, form_flags, feedback.
        """
        if self._exercise is None:
            return {
                "rep_count": 0,
                "total_reps": 0,
                "set_reps": 0,
                "good_reps": 0,
                "bad_reps": 0,
                "phase": "standing",
                "form_flags": [],
                "feedback": "No exercise selected.",
            }

        result = self._exercise.update(landmarks, angles)

        self.total_reps = result.get("rep_count", self.total_reps)
        self.good_reps = result.get("good_reps", self.good_reps)
        self.bad_reps = result.get("bad_reps", self.bad_reps)
        self.current_set_good = max(0, self.good_reps - self.set_start_good)
        self.current_set_bad = max(0, self.bad_reps - self.set_start_bad)

        result["total_reps"] = self.total_reps
        result["set_reps"] = max(0, self.total_reps - self.set_start_reps)

        return result

    def reset(self) -> None:
        """Reset the active exercise and aggregate counters."""
        if self._exercise is not None:
            self._exercise.reset()
        self.total_reps = 0
        self.good_reps = 0
        self.bad_reps = 0
        self.set_start_reps = 0
        self.set_start_good = 0
        self.set_start_bad = 0
        self.current_set_good = 0
        self.current_set_bad = 0
