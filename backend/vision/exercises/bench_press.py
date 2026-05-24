"""
Bench press exercise state machine (side view, elbow-driven).
"""

from typing import Any

from vision.form_analyser import (
    LEFT_ELBOW,
    LEFT_SHOULDER,
    RIGHT_ELBOW,
    RIGHT_SHOULDER,
)

from .base_exercise import BaseExercise

PHASE_TOP = "top"
PHASE_LOWERING = "lowering"
PHASE_BOTTOM = "bottom"
PHASE_PRESSING = "pressing"

TOP_THRESHOLD = 160.0
LOWERING_THRESHOLD = 130.0
BOTTOM_THRESHOLD = 90.0
PRESSING_THRESHOLD = 100.0
DEPTH_REQUIRED = 90.0
FLARE_THRESHOLD = 0.10


class BenchPress(BaseExercise):
    """Bench press rep counter using shoulder–elbow–wrist angles (side view)."""

    CAMERA_ANGLE = "side"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.phase: str = PHASE_TOP
        self.rep_count: int = 0
        self.good_reps: int = 0
        self.bad_reps: int = 0
        self._depth_achieved_this_rep: bool = False
        self._prev_phase: str = PHASE_TOP
        self._peak_elbow_angle: float = 0.0

    def _avg_elbow(self, angles: dict[str, float]) -> float:
        return (angles.get("left_elbow", 0.0) + angles.get("right_elbow", 0.0)) / 2.0

    def _check_flared_elbows(self, landmarks: list[dict[str, Any]]) -> bool:
        if len(landmarks) < 33:
            return False

        left_elbow_x = float(landmarks[LEFT_ELBOW]["x"])
        left_shoulder_x = float(landmarks[LEFT_SHOULDER]["x"])
        right_elbow_x = float(landmarks[RIGHT_ELBOW]["x"])
        right_shoulder_x = float(landmarks[RIGHT_SHOULDER]["x"])

        left_flared = abs(left_elbow_x - left_shoulder_x) > FLARE_THRESHOLD
        right_flared = abs(right_elbow_x - right_shoulder_x) > FLARE_THRESHOLD

        # Flared = elbow further from body midline than shoulder (wider grip path)
        left_wider = abs(left_elbow_x - 0.5) > abs(left_shoulder_x - 0.5) + FLARE_THRESHOLD
        right_wider = abs(right_elbow_x - 0.5) > abs(right_shoulder_x - 0.5) + FLARE_THRESHOLD

        return left_flared or right_flared or left_wider or right_wider

    def _build_feedback(
        self,
        phase: str,
        flared: bool,
        rep_completed_good: bool,
        rep_completed_bad: bool,
    ) -> str:
        if flared:
            return "Tuck your elbows slightly"

        if rep_completed_good:
            return f"Rep {self.rep_count} — locked out!"

        if rep_completed_bad:
            return "Press to full lockout"

        if phase == PHASE_TOP:
            return "Ready. Lower with control."

        if phase == PHASE_LOWERING:
            return "Control the descent"

        if phase == PHASE_BOTTOM:
            return "Touch and press!"

        if phase == PHASE_PRESSING:
            return "Drive to lockout"

        return "Ready. Lower with control."

    def update(
        self,
        landmarks: list[dict[str, Any]],
        angles: dict[str, float],
    ) -> dict[str, Any]:
        avg_elbow = self._avg_elbow(angles)
        form_flags: list[str] = []
        rep_completed_good = False
        rep_completed_bad = False

        self._prev_phase = self.phase
        self._peak_elbow_angle = max(self._peak_elbow_angle, avg_elbow)

        if avg_elbow < DEPTH_REQUIRED:
            self._depth_achieved_this_rep = True

        if self.phase == PHASE_TOP:
            if avg_elbow < LOWERING_THRESHOLD:
                self.phase = PHASE_LOWERING
                self._depth_achieved_this_rep = False
                self._peak_elbow_angle = avg_elbow

        elif self.phase == PHASE_LOWERING:
            if avg_elbow < BOTTOM_THRESHOLD:
                self.phase = PHASE_BOTTOM
                self._depth_achieved_this_rep = True
            elif avg_elbow > TOP_THRESHOLD:
                self.phase = PHASE_TOP

        elif self.phase == PHASE_BOTTOM:
            if avg_elbow > PRESSING_THRESHOLD:
                self.phase = PHASE_PRESSING
                if not self._depth_achieved_this_rep:
                    form_flags.append("no_lockout")

        elif self.phase == PHASE_PRESSING:
            if avg_elbow > TOP_THRESHOLD:
                self.rep_count += 1
                if self._depth_achieved_this_rep and self._peak_elbow_angle >= TOP_THRESHOLD:
                    self.good_reps += 1
                    form_flags.append("good_rep")
                    rep_completed_good = True
                else:
                    self.bad_reps += 1
                    if self._peak_elbow_angle < TOP_THRESHOLD:
                        form_flags.append("no_lockout")
                    rep_completed_bad = True

                self.phase = PHASE_TOP
                self._depth_achieved_this_rep = False
                self._peak_elbow_angle = 0.0

        flared = self._check_flared_elbows(landmarks)
        if flared:
            form_flags.append("flared_elbows")

        feedback = self._build_feedback(
            self.phase,
            flared,
            rep_completed_good,
            rep_completed_bad,
        )

        return {
            "rep_count": self.rep_count,
            "good_reps": self.good_reps,
            "bad_reps": self.bad_reps,
            "phase": self.phase,
            "form_flags": form_flags,
            "feedback": feedback,
        }
