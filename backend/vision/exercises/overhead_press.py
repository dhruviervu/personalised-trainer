"""
Overhead press (strict press) exercise state machine.
"""

from typing import Any

from .base_exercise import BaseExercise

PHASE_RACK = "rack"
PHASE_PRESSING = "pressing"
PHASE_LOCKOUT = "lockout"
PHASE_LOWERING = "lowering"

RACK_THRESHOLD = 90.0
PRESSING_THRESHOLD = 100.0
LOCKOUT_THRESHOLD = 165.0
LOWERING_THRESHOLD = 140.0
FORWARD_LEAN_THRESHOLD = 20.0


class OverheadPress(BaseExercise):
    """Overhead press rep counter using elbow and back angles."""

    CAMERA_ANGLE = "front"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.phase: str = PHASE_RACK
        self.rep_count: int = 0
        self.good_reps: int = 0
        self.bad_reps: int = 0
        self._lockout_achieved_this_rep: bool = False
        self._prev_phase: str = PHASE_RACK
        self._peak_elbow: float = 0.0

    def _avg_elbow(self, angles: dict[str, float]) -> float:
        return (angles.get("left_elbow", 0.0) + angles.get("right_elbow", 0.0)) / 2.0

    def _build_feedback(
        self,
        phase: str,
        forward_lean: bool,
        rep_completed_good: bool,
        rep_completed_bad: bool,
    ) -> str:
        if forward_lean:
            return "Stand tall — you're leaning back"

        if rep_completed_good:
            return f"Rep {self.rep_count} — full lockout!"

        if rep_completed_bad:
            return "Press to full lockout overhead"

        if phase == PHASE_RACK:
            return "Ready. Brace and press."

        if phase == PHASE_PRESSING:
            return "Drive it up"

        if phase == PHASE_LOCKOUT:
            return "Locked out — lower with control"

        if phase == PHASE_LOWERING:
            return "Lower with control"

        return "Ready. Brace and press."

    def update(
        self,
        landmarks: list[dict[str, Any]],
        angles: dict[str, float],
    ) -> dict[str, Any]:
        avg_elbow = self._avg_elbow(angles)
        back_angle = float(angles.get("back_angle", 0.0))
        form_flags: list[str] = []
        rep_completed_good = False
        rep_completed_bad = False

        self._prev_phase = self.phase
        self._peak_elbow = max(self._peak_elbow, avg_elbow)

        if avg_elbow >= LOCKOUT_THRESHOLD:
            self._lockout_achieved_this_rep = True

        if self.phase == PHASE_RACK:
            if avg_elbow > PRESSING_THRESHOLD:
                self.phase = PHASE_PRESSING
                self._lockout_achieved_this_rep = False
                self._peak_elbow = avg_elbow

        elif self.phase == PHASE_PRESSING:
            if avg_elbow >= LOCKOUT_THRESHOLD:
                self.phase = PHASE_LOCKOUT
                self._lockout_achieved_this_rep = True
            elif avg_elbow < RACK_THRESHOLD:
                self.phase = PHASE_RACK

        elif self.phase == PHASE_LOCKOUT:
            if avg_elbow < LOWERING_THRESHOLD:
                self.phase = PHASE_LOWERING

        elif self.phase == PHASE_LOWERING:
            if avg_elbow < RACK_THRESHOLD:
                self.rep_count += 1
                if self._lockout_achieved_this_rep and self._peak_elbow >= LOCKOUT_THRESHOLD:
                    self.good_reps += 1
                    form_flags.append("good_rep")
                    rep_completed_good = True
                else:
                    self.bad_reps += 1
                    form_flags.append("no_lockout")
                    rep_completed_bad = True

                self.phase = PHASE_RACK
                self._lockout_achieved_this_rep = False
                self._peak_elbow = 0.0

        forward_lean = back_angle > FORWARD_LEAN_THRESHOLD
        if forward_lean:
            form_flags.append("forward_lean")

        if (
            self._prev_phase == PHASE_LOWERING
            and self.phase == PHASE_RACK
            and rep_completed_bad
            and "no_lockout" not in form_flags
        ):
            form_flags.append("no_lockout")

        feedback = self._build_feedback(
            self.phase,
            forward_lean,
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
