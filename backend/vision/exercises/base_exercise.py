"""
Abstract base class for exercise state machines.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseExercise(ABC):
    """Base interface for rep counting and form feedback per exercise."""

    @abstractmethod
    def update(
        self,
        landmarks: list[dict[str, Any]],
        angles: dict[str, float],
    ) -> dict[str, Any]:
        """
        Process one frame of pose data.

        Returns dict with keys: rep_count, phase, form_flags, feedback.
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset exercise state (reps, phase machine, flags)."""
