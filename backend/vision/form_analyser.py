"""
Joint angle calculations from MediaPipe pose landmarks.
"""

import math
from typing import Any

import numpy as np

# MediaPipe Pose landmark indices
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28
LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32


def calculate_angle(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """
    Calculate the angle at vertex b formed by points a-b-c.

    Uses the dot product method. Returns angle in degrees (0–180).
    """
    a_vec = np.array([a[0] - b[0], a[1] - b[1]], dtype=np.float64)
    c_vec = np.array([c[0] - b[0], c[1] - b[1]], dtype=np.float64)

    norm_a = np.linalg.norm(a_vec)
    norm_c = np.linalg.norm(c_vec)

    if norm_a < 1e-8 or norm_c < 1e-8:
        return 0.0

    cos_angle = np.clip(np.dot(a_vec, c_vec) / (norm_a * norm_c), -1.0, 1.0)
    return float(math.degrees(math.acos(cos_angle)))


def calculate_back_angle(
    shoulder: tuple[float, float],
    hip: tuple[float, float],
    vertical: bool = True,
) -> float:
    """
    Angle of the torso from vertical (degrees).

    Uses mid-shoulder to mid-hip vector compared against the vertical axis.
    """
    if vertical:
        torso = np.array([shoulder[0] - hip[0], shoulder[1] - hip[1]], dtype=np.float64)
        # Vertical reference points downward in normalised image coords (y increases downward)
        vertical_ref = np.array([0.0, -1.0], dtype=np.float64)

        norm_torso = np.linalg.norm(torso)
        if norm_torso < 1e-8:
            return 0.0

        cos_angle = np.clip(np.dot(torso, vertical_ref) / norm_torso, -1.0, 1.0)
        return float(math.degrees(math.acos(cos_angle)))

    return calculate_angle(shoulder, hip, (hip[0], hip[1] - 0.1))


def _landmark_xy(landmarks: list[dict[str, Any]], index: int) -> tuple[float, float]:
    """Extract (x, y) from a landmark dict."""
    lm = landmarks[index]
    return (float(lm["x"]), float(lm["y"]))


class FormAnalyser:
    """Derives joint angles from a list of 33 pose landmarks."""

    def __init__(self, landmarks: list[dict[str, Any]] | None) -> None:
        self.landmarks = landmarks or []

    def get_angles(self) -> dict[str, float]:
        """
        Compute knee, hip, and back angles from the current landmarks.

        Returns zeros if landmarks are missing or incomplete.
        """
        if len(self.landmarks) < 33:
            return {
                "left_knee": 0.0,
                "right_knee": 0.0,
                "left_hip": 0.0,
                "right_hip": 0.0,
                "back_angle": 0.0,
            }

        left_hip = _landmark_xy(self.landmarks, LEFT_HIP)
        right_hip = _landmark_xy(self.landmarks, RIGHT_HIP)
        left_knee = _landmark_xy(self.landmarks, LEFT_KNEE)
        right_knee = _landmark_xy(self.landmarks, RIGHT_KNEE)
        left_ankle = _landmark_xy(self.landmarks, LEFT_ANKLE)
        right_ankle = _landmark_xy(self.landmarks, RIGHT_ANKLE)
        left_shoulder = _landmark_xy(self.landmarks, LEFT_SHOULDER)
        right_shoulder = _landmark_xy(self.landmarks, RIGHT_SHOULDER)

        mid_shoulder = (
            (left_shoulder[0] + right_shoulder[0]) / 2.0,
            (left_shoulder[1] + right_shoulder[1]) / 2.0,
        )
        mid_hip = (
            (left_hip[0] + right_hip[0]) / 2.0,
            (left_hip[1] + right_hip[1]) / 2.0,
        )

        return {
            "left_knee": calculate_angle(left_hip, left_knee, left_ankle),
            "right_knee": calculate_angle(right_hip, right_knee, right_ankle),
            "left_hip": calculate_angle(left_shoulder, left_hip, left_knee),
            "right_hip": calculate_angle(right_shoulder, right_hip, right_knee),
            "back_angle": calculate_back_angle(mid_shoulder, mid_hip),
        }

    def get_elbow_angles(self) -> dict[str, float]:
        """Elbow flexion angles (shoulder–elbow–wrist) for left and right arms."""
        if len(self.landmarks) < 33:
            return {"left_elbow": 0.0, "right_elbow": 0.0}

        left_shoulder = _landmark_xy(self.landmarks, LEFT_SHOULDER)
        right_shoulder = _landmark_xy(self.landmarks, RIGHT_SHOULDER)
        left_elbow = _landmark_xy(self.landmarks, LEFT_ELBOW)
        right_elbow = _landmark_xy(self.landmarks, RIGHT_ELBOW)
        left_wrist = _landmark_xy(self.landmarks, LEFT_WRIST)
        right_wrist = _landmark_xy(self.landmarks, RIGHT_WRIST)

        return {
            "left_elbow": calculate_angle(left_shoulder, left_elbow, left_wrist),
            "right_elbow": calculate_angle(right_shoulder, right_elbow, right_wrist),
        }

    def get_hip_hinge_angle(self) -> float:
        """
        Average hip hinge angle (shoulder–hip–knee at the hip).

        Measures quality of the hip hinge for deadlift-style movements.
        """
        if len(self.landmarks) < 33:
            return 0.0

        angles = self.get_angles()
        return (angles["left_hip"] + angles["right_hip"]) / 2.0

    def get_wrist_positions(self) -> dict[str, dict[str, float]]:
        """Normalised x/y positions for left and right wrists."""
        if len(self.landmarks) < 33:
            return {
                "left_wrist": {"x": 0.0, "y": 0.0},
                "right_wrist": {"x": 0.0, "y": 0.0},
            }

        left = _landmark_xy(self.landmarks, LEFT_WRIST)
        right = _landmark_xy(self.landmarks, RIGHT_WRIST)

        return {
            "left_wrist": {"x": left[0], "y": left[1]},
            "right_wrist": {"x": right[0], "y": right[1]},
        }
