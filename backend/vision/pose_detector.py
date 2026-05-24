"""
MediaPipe Pose detection wrapper (Tasks API).

Uses PoseLandmarker from mediapipe.tasks — the supported API in MediaPipe 0.10+.
Detection thresholds match the Phase 1 spec (0.7 min confidence).
"""

import logging
import os
import urllib.request
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_FILENAME = "pose_landmarker_lite.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)


class PoseDetector:
    """Detects human pose landmarks in BGR video frames using MediaPipe PoseLandmarker."""

    def __init__(self) -> None:
        model_path = self._ensure_model()
        base_options = mp_tasks.BaseOptions(model_asset_path=str(model_path))
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.7,
            min_pose_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._timestamp_ms = 0

    def _ensure_model(self) -> Path:
        """Download the pose landmarker model if it is not already cached locally."""
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODEL_DIR / MODEL_FILENAME

        if not model_path.exists():
            logger.info("Downloading pose landmarker model to %s", model_path)
            urllib.request.urlretrieve(MODEL_URL, model_path)

        return model_path

    def process_frame(self, frame_bgr) -> list[dict[str, Any]] | None:
        """
        Run pose estimation on a BGR OpenCV frame.

        Returns a list of 33 normalised landmark dicts, or None if no pose is found.
        """
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        result = self._landmarker.detect_for_video(mp_image, self._timestamp_ms)
        self._timestamp_ms += 33  # ~30 fps monotonic timestamp for video mode

        if not result.pose_landmarks:
            return None

        pose_landmarks = result.pose_landmarks[0]
        landmarks: list[dict[str, Any]] = []
        for lm in pose_landmarks:
            landmarks.append(
                {
                    "x": float(lm.x),
                    "y": float(lm.y),
                    "z": float(lm.z),
                    "visibility": float(lm.visibility),
                }
            )
        return landmarks

    def close(self) -> None:
        """Release MediaPipe resources."""
        self._landmarker.close()
