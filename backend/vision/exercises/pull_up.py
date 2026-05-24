"""
Pull-up exercise state machine (front view).
"""

from typing import Any

from vision.form_analyser import FormAnalyser, LEFT_SHOULDER, RIGHT_SHOULDER

from .base_exercise import BaseExercise

PHASE_DEAD_HANG = "dead_hang"
PHASE_PULLING = "pulling"
PHASE_TOP = "top"
PHASE_LOWERING = "lowering"

DEAD_HANG_THRESHOLD = 160.0
PULLING_THRESHOLD = 140.0
TOP_ELBOW_THRESHOLD = 70.0
LOWERING_THRESHOLD = 90.0


class PullUp(BaseExercise):
    """Pull-up rep counter using elbow angles and wrist height vs shoulders."""

    CAMERA_ANGLE = "front"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.phase: str = PHASE_DEAD_HANG
        self.rep_count: int = 0
        self.good_reps: int = 0
        self.bad_reps: int = 0
        self._chin_over_bar_this_rep: bool = False
        self._prev_phase: str = PHASE_DEAD_HANG

    def _avg_elbow(self, angles: dict[str, float]) -> float:
        return (angles.get("left_elbow", 0.0) + angles.get("right_elbow", 0.0)) / 2.0

    def _chin_over_bar(self, landmarks: list[dict[str, Any]]) -> bool:
        """Wrist y above shoulder y (smaller y = higher in image coordinates)."""
        if len(landmarks) < 33:
            return False

        analyser = FormAnalyser(landmarks)
        wrists = analyser.get_wrist_positions()

        left_shoulder_y = float(landmarks[LEFT_SHOULDER]["y"])
        right_shoulder_y = float(landmarks[RIGHT_SHOULDER]["y"])
        mid_shoulder_y = (left_shoulder_y + right_shoulder_y) / 2.0

        left_wrist_y = wrists["left_wrist"]["y"]
        right_wrist_y = wrists["right_wrist"]["y"]
        avg_wrist_y = (left_wrist_y + right_wrist_y) / 2.0

        return avg_wrist_y < mid_shoulder_y

    def _build_feedback(
        self,
        phase: str,
        no_chin: bool,
        rep_completed_good: bool,
        rep_completed_bad: bool,
    ) -> str:
        if no_chin:
            return "Pull higher — chin over bar"

        if rep_completed_good:
            return f"Rep {self.rep_count} — full rep!"

        if rep_completed_bad:
            return "Pull higher — chin over bar"

        if phase == PHASE_DEAD_HANG:
            return "Hang fully. Pull when ready."

        if phase == PHASE_PULLING:
            return "Drive your elbows down"

        if phase == PHASE_TOP:
            return "Hold — lower with control"

        if phase == PHASE_LOWERING:
            return "Lower with control"

        return "Hang fully. Pull when ready."

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
        chin_over = self._chin_over_bar(landmarks)

        if self.phase == PHASE_DEAD_HANG:
            if avg_elbow < PULLING_THRESHOLD:
                self.phase = PHASE_PULLING
                self._chin_over_bar_this_rep = False

        elif self.phase == PHASE_PULLING:
            if avg_elbow < TOP_ELBOW_THRESHOLD and chin_over:
                self.phase = PHASE_TOP
                self._chin_over_bar_this_rep = True
            elif avg_elbow < TOP_ELBOW_THRESHOLD:
                self.phase = PHASE_TOP
                self._chin_over_bar_this_rep = False

        elif self.phase == PHASE_TOP:
            if chin_over:
                self._chin_over_bar_this_rep = True
            if avg_elbow > LOWERING_THRESHOLD:
                self.phase = PHASE_LOWERING
                if not self._chin_over_bar_this_rep:
                    form_flags.append("no_chin_over_bar")

        elif self.phase == PHASE_LOWERING:
            if avg_elbow > DEAD_HANG_THRESHOLD:
                self.rep_count += 1
                if self._chin_over_bar_this_rep:
                    self.good_reps += 1
                    form_flags.append("good_rep")
                    rep_completed_good = True
                else:
                    self.bad_reps += 1
                    form_flags.append("no_chin_over_bar")
                    rep_completed_bad = True

                self.phase = PHASE_DEAD_HANG
                self._chin_over_bar_this_rep = False

        no_chin = (
            self.phase == PHASE_TOP
            and not self._chin_over_bar_this_rep
            and not chin_over
        )
        if no_chin or "no_chin_over_bar" in form_flags:
            if "no_chin_over_bar" not in form_flags and self.phase == PHASE_TOP:
                form_flags.append("no_chin_over_bar")

        feedback = self._build_feedback(
            self.phase,
            no_chin or "no_chin_over_bar" in form_flags,
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
