"""
Exercise registry — maps exercise keys to state machine classes.
"""

from typing import Type

from .base_exercise import BaseExercise
from .bench_press import BenchPress
from .deadlift import Deadlift
from .overhead_press import OverheadPress
from .pull_up import PullUp
from .romanian_deadlift import RomanianDeadlift
from .squat import Squat

EXERCISE_REGISTRY: dict[str, Type[BaseExercise]] = {
    "squat": Squat,
    "deadlift": Deadlift,
    "bench_press": BenchPress,
    "overhead_press": OverheadPress,
    "romanian_deadlift": RomanianDeadlift,
    "pull_up": PullUp,
}

VALID_EXERCISES = ", ".join(sorted(EXERCISE_REGISTRY.keys()))


def get_exercise(name: str) -> BaseExercise:
    """
    Instantiate an exercise state machine by registry key.

    Raises:
        ValueError: If the exercise name is not registered.
    """
    key = name.strip().lower()
    exercise_cls = EXERCISE_REGISTRY.get(key)

    if exercise_cls is None:
        raise ValueError(
            f"Unknown exercise: '{name}'. Valid exercises: {VALID_EXERCISES}"
        )

    return exercise_cls()
