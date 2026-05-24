"""
Squat exercise state machine and form analysis.
"""

from typing import Any

from vision.form_analyser import LEFT_ANKLE, LEFT_KNEE, RIGHT_ANKLE, RIGHT_KNEE

from .base_exercise import BaseExercise

# Phase names
PHASE_STANDING = "standing"
PHASE_DESCENDING = "descending"
PHASE_BOTTOM = "bottom"
PHASE_ASCENDING = "ascending"

# Knee angle thresholds (degrees, average of left and right)
STANDING_THRESHOLD = 160.0
DESCENDING_THRESHOLD = 140.0
BOTTOM_THRESHOLD = 95.0
ASCENDING_THRESHOLD = 110.0
DEPTH_REQUIRED = 95.0

# Knees caving: inward offset as fraction of frame width (normalised coords)
KNEE_CAVE_THRESHOLD = 0.05


class Squat(BaseExercise):
    """
    Squat rep counter with phase state machine and real-time form flags.

    Rep completes when returning to standing from ascending, only if sufficient
  depth was reached at the bottom of the movement.
    """

    CAMERA_ANGLE = "front"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.phase: str = PHASE_STANDING
        self.rep_count: int = 0
        self.good_reps: int = 0
        self.bad_reps: int = 0
        self._reached_bottom_depth: bool = False
        self._depth_achieved_this_rep: bool = False
        self._was_at_bottom: bool = False
        self._emit_good_rep_flag: bool = False
        self._prev_phase: str = PHASE_STANDING

    def _avg_knee_angle(self, angles: dict[str, float]) -> float:
        return (angles["left_knee"] + angles["right_knee"]) / 2.0

    def _check_knees_caving(self, landmarks: list[dict[str, Any]]) -> bool:
        """True if either knee caves inward past the ankle by >5% frame width."""
        if len(landmarks) < 33:
            return False

        left_knee_x = float(landmarks[LEFT_KNEE]["x"])
        left_ankle_x = float(landmarks[LEFT_ANKLE]["x"])
        right_knee_x = float(landmarks[RIGHT_KNEE]["x"])
        right_ankle_x = float(landmarks[RIGHT_ANKLE]["x"])

        # Left knee caves inward (toward image centre / +x)
        left_caving = (left_knee_x - left_ankle_x) > KNEE_CAVE_THRESHOLD
        # Right knee caves inward (toward image centre / -x)
        right_caving = (right_ankle_x - right_knee_x) > KNEE_CAVE_THRESHOLD

        return left_caving or right_caving

    def _build_feedback(
        self,
        phase: str,
        avg_knee: float,
        knees_caving: bool,
        rep_completed_good: bool,
        rep_completed_bad: bool,
    ) -> str:
        if knees_caving:
            return "Knees out!"

        if rep_completed_good:
            return f"Rep {self.rep_count} — good rep!"

        if rep_completed_bad:
            return f"Rep {self.rep_count} — didn't hit depth"

        if phase == PHASE_STANDING:
            return "Ready. Begin your squat."

        if phase == PHASE_DESCENDING:
            if avg_knee > 120.0:
                return "Keep going down"
            return "Almost there — hit parallel"

        if phase == PHASE_BOTTOM:
            if self._depth_achieved_this_rep:
                return "Good depth! Drive up."
            return "Go deeper — hit parallel"

        if phase == PHASE_ASCENDING:
            return "Drive through your heels"

        return "Ready. Begin your squat."

    def update(
        self,
        landmarks: list[dict[str, Any]],
        angles: dict[str, float],
    ) -> dict[str, Any]:
        avg_knee = self._avg_knee_angle(angles)
        form_flags: list[str] = []
        rep_completed_good = False
        rep_completed_bad = False

        self._emit_good_rep_flag = False
        self._prev_phase = self.phase

        # Track depth while in bottom phase
        if avg_knee < DEPTH_REQUIRED:
            self._depth_achieved_this_rep = True

        # --- State machine transitions ---
        if self.phase == PHASE_STANDING:
            if avg_knee < DESCENDING_THRESHOLD:
                self.phase = PHASE_DESCENDING
                self._depth_achieved_this_rep = False

        elif self.phase == PHASE_DESCENDING:
            if avg_knee < BOTTOM_THRESHOLD:
                self.phase = PHASE_BOTTOM
                self._was_at_bottom = True
                self._depth_achieved_this_rep = True
            elif avg_knee > STANDING_THRESHOLD:
                # Aborted rep — returned to standing without depth
                self.phase = PHASE_STANDING

        elif self.phase == PHASE_BOTTOM:
            if avg_knee > ASCENDING_THRESHOLD:
                self.phase = PHASE_ASCENDING
                if not self._depth_achieved_this_rep:
                    form_flags.append("insufficient_depth")

        elif self.phase == PHASE_ASCENDING:
            if avg_knee > STANDING_THRESHOLD:
                # Rep complete
                self.rep_count += 1
                if self._depth_achieved_this_rep:
                    self.good_reps += 1
                    form_flags.append("good_rep")
                    self._emit_good_rep_flag = True
                    rep_completed_good = True
                else:
                    self.bad_reps += 1
                    if "insufficient_depth" not in form_flags:
                        form_flags.append("insufficient_depth")
                    rep_completed_bad = True

                self.phase = PHASE_STANDING
                self._was_at_bottom = False
                self._depth_achieved_this_rep = False

        # Insufficient depth when leaving bottom without ever hitting depth
        if (
            self._prev_phase == PHASE_BOTTOM
            and self.phase == PHASE_ASCENDING
            and not self._depth_achieved_this_rep
            and "insufficient_depth" not in form_flags
        ):
            form_flags.append("insufficient_depth")

        knees_caving = self._check_knees_caving(landmarks)
        if knees_caving:
            form_flags.append("knees_caving")

        feedback = self._build_feedback(
            self.phase,
            avg_knee,
            knees_caving,
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
