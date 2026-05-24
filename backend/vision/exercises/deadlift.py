"""
Conventional deadlift exercise state machine (side view).
"""

from typing import Any

from .base_exercise import BaseExercise

PHASE_STANDING = "standing"
PHASE_HINGING = "hinging"
PHASE_BOTTOM = "bottom"
PHASE_LIFTING = "lifting"

STANDING_THRESHOLD = 160.0
HINGING_THRESHOLD = 140.0
BOTTOM_THRESHOLD = 70.0
LIFTING_THRESHOLD = 90.0
DEPTH_REQUIRED = 70.0
BACK_ROUND_THRESHOLD = 30.0


class Deadlift(BaseExercise):
    """Deadlift rep counter using hip hinge and back angle (side view)."""

    CAMERA_ANGLE = "side"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.phase: str = PHASE_STANDING
        self.rep_count: int = 0
        self.good_reps: int = 0
        self.bad_reps: int = 0
        self._depth_achieved_this_rep: bool = False
        self._prev_phase: str = PHASE_STANDING
        self._max_elbow_lockout: float = 0.0

    def _hip_hinge(self, angles: dict[str, float]) -> float:
        if "hip_hinge" in angles:
            return float(angles["hip_hinge"])
        return (angles.get("left_hip", 0.0) + angles.get("right_hip", 0.0)) / 2.0

    def _build_feedback(
        self,
        phase: str,
        back_rounding: bool,
        shallow_hinge: bool,
        rep_completed_good: bool,
        rep_completed_bad: bool,
    ) -> str:
        if back_rounding and phase == PHASE_BOTTOM:
            return "Chest up — back is rounding"

        if rep_completed_good:
            return f"Rep {self.rep_count} — good lift!"

        if rep_completed_bad or shallow_hinge:
            return "Hinge deeper — get the bar to the floor"

        if phase == PHASE_STANDING:
            return "Ready. Hinge at the hips."

        if phase == PHASE_HINGING:
            return "Keep your back flat"

        if phase == PHASE_BOTTOM:
            return "Back flat — drive through the floor"

        if phase == PHASE_LIFTING:
            return "Drive through the floor"

        return "Ready. Hinge at the hips."

    def update(
        self,
        landmarks: list[dict[str, Any]],
        angles: dict[str, float],
    ) -> dict[str, Any]:
        hip_hinge = self._hip_hinge(angles)
        back_angle = float(angles.get("back_angle", 0.0))
        form_flags: list[str] = []
        rep_completed_good = False
        rep_completed_bad = False
        shallow_hinge = False

        self._prev_phase = self.phase

        if hip_hinge < DEPTH_REQUIRED:
            self._depth_achieved_this_rep = True

        if self.phase == PHASE_STANDING:
            if hip_hinge < HINGING_THRESHOLD:
                self.phase = PHASE_HINGING
                self._depth_achieved_this_rep = False

        elif self.phase == PHASE_HINGING:
            if hip_hinge < BOTTOM_THRESHOLD:
                self.phase = PHASE_BOTTOM
                self._depth_achieved_this_rep = True
            elif hip_hinge > STANDING_THRESHOLD:
                self.phase = PHASE_STANDING

        elif self.phase == PHASE_BOTTOM:
            if hip_hinge > LIFTING_THRESHOLD:
                self.phase = PHASE_LIFTING
                if not self._depth_achieved_this_rep:
                    form_flags.append("shallow_hinge")

        elif self.phase == PHASE_LIFTING:
            if hip_hinge > STANDING_THRESHOLD:
                self.rep_count += 1
                if self._depth_achieved_this_rep:
                    self.good_reps += 1
                    form_flags.append("good_rep")
                    rep_completed_good = True
                else:
                    self.bad_reps += 1
                    form_flags.append("shallow_hinge")
                    shallow_hinge = True
                    rep_completed_bad = True

                self.phase = PHASE_STANDING
                self._depth_achieved_this_rep = False

        if (
            self._prev_phase == PHASE_BOTTOM
            and self.phase == PHASE_LIFTING
            and not self._depth_achieved_this_rep
            and "shallow_hinge" not in form_flags
        ):
            form_flags.append("shallow_hinge")

        back_rounding = self.phase == PHASE_BOTTOM and back_angle > BACK_ROUND_THRESHOLD
        if back_rounding:
            form_flags.append("back_rounding")

        feedback = self._build_feedback(
            self.phase,
            back_rounding,
            shallow_hinge or "shallow_hinge" in form_flags,
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
