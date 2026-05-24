"""
Local JSON persistence for workout sessions (Phase 3 — file store until Phase 4 DB).
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SESSIONS_FILE = DATA_DIR / "sessions.json"

_file_lock = threading.Lock()


def _ensure_data_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SESSIONS_FILE.exists():
        SESSIONS_FILE.write_text(json.dumps({"sessions": []}, indent=2), encoding="utf-8")


def _load_data() -> dict[str, Any]:
    _ensure_data_file()
    with SESSIONS_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _save_data(data: dict[str, Any]) -> None:
    _ensure_data_file()
    with SESSIONS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


class SessionLogger:
    """Append-only session log backed by backend/data/sessions.json."""

    def start_session(self, exercise: str, goal: str) -> str:
        """Create a new in-progress session and return its UUID."""
        session_id = str(uuid.uuid4())
        entry = {
            "session_id": session_id,
            "exercise": exercise,
            "goal": goal,
            "date": datetime.now(timezone.utc).isoformat(),
            "sets": [],
            "progression_advice": None,
            "completed": False,
        }

        with _file_lock:
            data = _load_data()
            data["sessions"].append(entry)
            _save_data(data)

        return session_id

    def log_set(
        self,
        session_id: str,
        set_data: dict[str, Any],
        rpe: int | None,
        coach_feedback: str,
        weight_kg: float,
        set_number: int,
    ) -> None:
        """Append a completed set to the session immediately."""
        set_entry = {
            "set_number": set_number,
            "weight_kg": weight_kg,
            "reps_completed": set_data.get("reps_completed", 0),
            "good_reps": set_data.get("good_reps", 0),
            "bad_reps": set_data.get("bad_reps", 0),
            "form_flags": set_data.get("form_flags", []),
            "avg_angles": set_data.get("avg_angles", {}),
            "rpe": rpe,
            "coach_feedback": coach_feedback,
        }

        with _file_lock:
            data = _load_data()
            for session in data["sessions"]:
                if session["session_id"] == session_id:
                    session["sets"].append(set_entry)
                    break
            _save_data(data)

    def update_last_set_rpe(self, session_id: str, rpe: int) -> None:
        """Update RPE on the most recently logged set."""
        with _file_lock:
            data = _load_data()
            for session in data["sessions"]:
                if session["session_id"] == session_id and session["sets"]:
                    session["sets"][-1]["rpe"] = rpe
                    break
            _save_data(data)

    def end_session(self, session_id: str, progression_advice: str) -> None:
        """Mark session complete and store progression advice."""
        with _file_lock:
            data = _load_data()
            for session in data["sessions"]:
                if session["session_id"] == session_id:
                    session["completed"] = True
                    session["progression_advice"] = progression_advice
                    break
            _save_data(data)

    def get_last_session(self, exercise: str) -> dict[str, Any] | None:
        """Return the most recent completed session for an exercise."""
        with _file_lock:
            data = _load_data()
            matches = [
                s
                for s in data["sessions"]
                if s.get("exercise") == exercise and s.get("completed")
            ]
            if not matches:
                return None
            return sorted(matches, key=lambda s: s.get("date", ""), reverse=True)[0]

    def get_all_sessions(self) -> list[dict[str, Any]]:
        """Return all sessions newest first."""
        with _file_lock:
            data = _load_data()
            return sorted(
                data.get("sessions", []),
                key=lambda s: s.get("date", ""),
                reverse=True,
            )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Return a single session by ID."""
        with _file_lock:
            data = _load_data()
            for session in data["sessions"]:
                if session["session_id"] == session_id:
                    return session
            return None
