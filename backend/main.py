"""
FastAPI server: real-time pose WebSocket + Groq AI coach + SQLite persistence.
"""

import base64
import binascii
import collections
import json
import logging
from typing import Any

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from ai.coach import FALLBACK_MESSAGE, GroqCoach, parse_rpe_from_message
from ai.progression import ProgressionEngine
from ai.set_aggregator import SetAggregator
from database import crud
from database.connection import get_db, init_db
from vision.exercises.base_exercise import BaseExercise
from vision.exercises.registry import EXERCISE_REGISTRY, VALID_EXERCISES, get_exercise
from vision.form_analyser import FormAnalyser
from vision.pose_detector import PoseDetector
from vision.rep_counter import RepCounter

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Personal Trainer", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

progression_engine = ProgressionEngine()

active_coaches: dict[str, GroqCoach] = {}
active_sessions: dict[str, dict[str, Any]] = {}
active_aggregators: dict[str, SetAggregator] = {}

SMOOTHED_ANGLE_KEYS = (
    "left_knee",
    "right_knee",
    "left_hip",
    "right_hip",
    "back_angle",
    "left_elbow",
    "right_elbow",
    "hip_hinge",
    "left_wrist_x",
    "left_wrist_y",
    "right_wrist_x",
    "right_wrist_y",
)
SMOOTHING_WINDOW = 3
NO_POSE_FEEDBACK = "No pose detected — step back so your full body is visible"


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Database initialised")


class SessionStartBody(BaseModel):
    exercise: str
    goal: str
    weight_kg: float = Field(gt=0)


class SetCompleteBody(BaseModel):
    set_data: dict[str, Any]
    weight_kg: float = Field(gt=0)


class ChatBody(BaseModel):
    message: str


class BodyweightBody(BaseModel):
    weight_kg: float = Field(gt=0)


def _decode_frame(base64_jpeg: str) -> np.ndarray | None:
    try:
        raw = base64.b64decode(base64_jpeg, validate=True)
        buffer = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        return frame
    except (binascii.Error, ValueError, cv2.error) as exc:
        logger.warning("Frame decode failed: %s", exc)
        return None


def _collect_raw_angles(landmarks: list[dict[str, Any]]) -> dict[str, float]:
    analyser = FormAnalyser(landmarks)
    angles = analyser.get_angles()
    angles.update(analyser.get_elbow_angles())
    angles["hip_hinge"] = analyser.get_hip_hinge_angle()
    wrists = analyser.get_wrist_positions()
    angles["left_wrist_x"] = wrists["left_wrist"]["x"]
    angles["left_wrist_y"] = wrists["left_wrist"]["y"]
    angles["right_wrist_x"] = wrists["right_wrist"]["x"]
    angles["right_wrist_y"] = wrists["right_wrist"]["y"]
    return angles


def _smooth_angles(
    history: collections.deque[dict[str, float]],
    raw_angles: dict[str, float],
) -> dict[str, float]:
    history.append(raw_angles)
    if len(history) == 1:
        return dict(raw_angles)

    smoothed: dict[str, float] = {}
    for key in SMOOTHED_ANGLE_KEYS:
        if key not in raw_angles:
            continue
        values = [frame[key] for frame in history if key in frame]
        if values:
            smoothed[key] = float(sum(values) / len(values))
    return smoothed


def _camera_angle_for(exercise: BaseExercise | None) -> str:
    if exercise is None:
        return "front"
    return getattr(type(exercise), "CAMERA_ANGLE", "front")


def _empty_response(
    feedback: str = NO_POSE_FEEDBACK,
    rep_counter: RepCounter | None = None,
    exercise: BaseExercise | None = None,
    phase: str = "standing",
) -> dict[str, Any]:
    return {
        "landmarks": [],
        "rep_count": rep_counter.total_reps if rep_counter else 0,
        "total_reps": rep_counter.total_reps if rep_counter else 0,
        "set_reps": (
            max(0, rep_counter.total_reps - rep_counter.set_start_reps)
            if rep_counter
            else 0
        ),
        "good_reps": rep_counter.good_reps if rep_counter else 0,
        "bad_reps": rep_counter.bad_reps if rep_counter else 0,
        "phase": phase,
        "form_flags": [],
        "angles": {key: 0.0 for key in SMOOTHED_ANGLE_KEYS[:5]},
        "feedback": feedback,
        "camera_angle": _camera_angle_for(exercise),
    }


def _build_response(
    landmarks: list[dict[str, Any]],
    rep_data: dict[str, Any],
    angles: dict[str, float],
    exercise: BaseExercise,
) -> dict[str, Any]:
    return {
        "landmarks": landmarks,
        "rep_count": rep_data["rep_count"],
        "total_reps": rep_data.get("total_reps", rep_data["rep_count"]),
        "set_reps": rep_data.get("set_reps", rep_data["rep_count"]),
        "good_reps": rep_data.get("good_reps", 0),
        "bad_reps": rep_data.get("bad_reps", 0),
        "phase": rep_data["phase"],
        "form_flags": rep_data["form_flags"],
        "angles": angles,
        "feedback": rep_data["feedback"],
        "camera_angle": _camera_angle_for(exercise),
    }


def _merge_set_data(
    exercise: str,
    body_set_data: dict[str, Any],
    session_id: str | None,
    weight_kg: float,
    set_number: int,
) -> dict[str, Any]:
    merged = dict(body_set_data)
    merged["exercise"] = exercise
    merged["weight_kg"] = weight_kg
    merged["set_number"] = set_number

    if session_id and session_id in active_aggregators:
        agg = active_aggregators[session_id]
        if agg.angle_samples:
            keys = agg.angle_samples[0].keys()
            avg_angles: dict[str, float] = {}
            for key in keys:
                values = [sample[key] for sample in agg.angle_samples if key in sample]
                if values:
                    avg_angles[key] = float(sum(values) / len(values))
            if avg_angles:
                merged["avg_angles"] = avg_angles

        server_flags = set(merged.get("form_flags", [])) | agg.form_flags_seen
        merged["form_flags"] = sorted(f for f in server_flags if f != "good_rep")

    return merged


def _build_session_summary_from_db(session) -> dict[str, Any]:
    sets = session.sets
    rpe_trend: list[int] = []
    flag_frequency: dict[str, int] = {}

    for set_entry in sets:
        if set_entry.rpe is not None:
            rpe_trend.append(int(set_entry.rpe))
        for flag in set_entry.form_flags or []:
            flag_frequency[flag] = flag_frequency.get(flag, 0) + 1

    return {
        "exercise": session.exercise,
        "goal": session.goal,
        "total_sets": len(sets),
        "sets": [
            {
                "set_number": s.set_number,
                "weight_kg": s.weight_kg,
                "reps_completed": s.reps_completed,
                "good_reps": s.good_reps,
                "rpe": s.rpe,
                "form_flags": s.form_flags,
                "form_score": s.form_score,
                "e1rm": s.e1rm,
            }
            for s in sets
        ],
        "rpe_trend": rpe_trend,
        "form_flag_frequency": flag_frequency,
    }


def _session_stats(session) -> dict[str, Any]:
    """Aggregate stats for every set in the session, grouped by exercise."""
    sets = session.sets or []
    total_reps = sum(s.reps_completed for s in sets)
    total_good = sum(s.good_reps for s in sets)
    form_score_percent = (
        round((total_good / total_reps) * 100, 1) if total_reps > 0 else 0.0
    )

    top_set = None
    session_e1rm = 0.0
    by_exercise: dict[str, dict[str, Any]] = {}

    for s in sets:
        angles = s.avg_angles if isinstance(s.avg_angles, dict) else {}
        exercise_name = angles.get("exercise") or session.exercise or "unknown"
        if exercise_name not in by_exercise:
            by_exercise[exercise_name] = {
                "sets": 0,
                "reps": 0,
                "good_reps": 0,
                "volume": 0.0,
                "form_scores": [],
            }
        bucket = by_exercise[exercise_name]
        bucket["sets"] += 1
        bucket["reps"] += s.reps_completed
        bucket["good_reps"] += s.good_reps
        bucket["volume"] += s.weight_kg * s.reps_completed
        bucket["form_scores"].append(float(s.form_score or 0))
        if s.e1rm > session_e1rm:
            session_e1rm = s.e1rm
            top_set = s

    exercises = []
    for exercise_name, data in by_exercise.items():
        scores = data["form_scores"]
        avg_form = round(sum(scores) / len(scores), 1) if scores else 0.0
        exercises.append(
            {
                "exercise": exercise_name,
                "sets": data["sets"],
                "reps": data["reps"],
                "volume_kg": round(data["volume"], 1),
                "form_score_percent": avg_form,
            }
        )

    return {
        "form_score_percent": form_score_percent,
        "total_sets": len(sets),
        "total_reps": total_reps,
        "top_set": (
            {
                "weight_kg": top_set.weight_kg,
                "reps": top_set.reps_completed,
                "e1rm": round(top_set.e1rm, 1),
                "exercise": (
                    (top_set.avg_angles or {}).get("exercise")
                    if isinstance(top_set.avg_angles, dict)
                    else session.exercise
                ),
            }
            if top_set
            else None
        ),
        "session_e1rm": round(session_e1rm, 1),
        "total_volume_kg": round(session.total_volume_kg or 0, 1),
        "exercises": exercises,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/session/start")
async def api_session_start(
    body: SessionStartBody,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    exercise = body.exercise.strip().lower()
    if exercise not in EXERCISE_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown exercise '{body.exercise}'. Valid: {VALID_EXERCISES}",
        )

    session = crud.create_session(db, exercise, body.goal)
    session_id = session.id

    coach = GroqCoach()
    try:
        opening_message = await coach.start_session(exercise, body.goal)
    except Exception as exc:
        logger.exception("Coach start failed: %s", exc)
        opening_message = FALLBACK_MESSAGE

    active_coaches[session_id] = coach
    active_sessions[session_id] = {
        "exercise": exercise,
        "goal": body.goal,
        "weight_kg": body.weight_kg,
        "set_number": 0,
        "awaiting_rpe": False,
        "session_had_pr": False,
    }
    active_aggregators[session_id] = SetAggregator()

    return {"session_id": session_id, "opening_message": opening_message}


@app.post("/api/session/{session_id}/set-complete")
async def api_set_complete(
    session_id: str,
    body: SetCompleteBody,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    meta = active_sessions[session_id]
    coach = active_coaches.get(session_id)
    if coach is None:
        raise HTTPException(status_code=404, detail="Coach not found for session")

    db_session = crud.get_session(db, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found in database")

    meta["set_number"] += 1
    set_number = meta["set_number"]

    set_data = _merge_set_data(
        meta["exercise"],
        body.set_data,
        session_id,
        body.weight_kg,
        set_number,
    )

    reps = int(set_data.get("reps_completed", 0))
    e1rm = crud.calculate_e1rm(body.weight_kg, reps)

    is_pr, _pr_record = crud.check_and_update_pr(
        db,
        crud.DEFAULT_USER_ID,
        meta["exercise"],
        body.weight_kg,
        reps,
        e1rm,
        session_id,
    )
    if is_pr:
        meta["session_had_pr"] = True

    # Log set first so progression engine includes this set in history
    coach_message = FALLBACK_MESSAGE
    set_data["exercise"] = meta["exercise"]
    avg_angles = dict(set_data.get("avg_angles") or {})
    avg_angles["exercise"] = meta["exercise"]
    set_data["avg_angles"] = avg_angles

    set_log = crud.log_set(
        db,
        session_id,
        set_data,
        rpe=None,
        coach_feedback="",
    )
    if set_log is not None:
        e1rm = set_log.e1rm

    recent_sets = crud.get_recent_sets_for_exercise(
        db, meta["exercise"], session_limit=3, include_session_id=session_id
    )
    analysis = progression_engine.analyze(
        meta["exercise"],
        recent_sets,
        meta["goal"],
        body.weight_kg,
    )

    extra_context_parts: list[str] = []
    if is_pr:
        extra_context_parts.append(f"By the way, that's a new PR! e1RM: {e1rm:.1f}kg")
    extra_context_parts.append(
        f"Progression analysis: {analysis['reasoning']} "
        f"Recommendation: {analysis['recommendation']} at {analysis['next_weight_kg']}kg."
    )
    extra_context = " ".join(extra_context_parts)

    try:
        coach_message = await coach.post_set_message(
            set_data,
            user_message=None,
            extra_context=extra_context,
        )
    except Exception as exc:
        logger.exception("Coach set-complete failed: %s", exc)
        coach_message = FALLBACK_MESSAGE

    if set_log is not None:
        set_log.coach_feedback = coach_message
        db.commit()

    meta["awaiting_rpe"] = True
    meta["last_weight_kg"] = body.weight_kg

    if session_id in active_aggregators:
        agg = active_aggregators[session_id]
        end_rep = int(body.set_data.get("end_rep_count", 0))
        end_good = int(body.set_data.get("end_good_reps", 0))
        end_bad = int(body.set_data.get("end_bad_reps", 0))
        agg.begin_set(end_rep, end_good, end_bad)

    return {
        "coach_message": coach_message,
        "awaiting_rpe": True,
        "is_pr": is_pr,
        "e1rm": round(e1rm, 1),
        "progression": analysis,
    }


@app.post("/api/session/{session_id}/chat")
async def api_session_chat(
    session_id: str,
    body: ChatBody,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    meta = active_sessions[session_id]
    coach = active_coaches.get(session_id)
    if coach is None:
        raise HTTPException(status_code=404, detail="Coach not found for session")

    try:
        coach_message = await coach.post_set_message({}, user_message=body.message)
    except Exception as exc:
        logger.exception("Coach chat failed: %s", exc)
        coach_message = FALLBACK_MESSAGE

    rpe = parse_rpe_from_message(body.message)
    if rpe is not None:
        crud.update_last_set_rpe(db, session_id, float(rpe))
        meta["awaiting_rpe"] = False

    return {"coach_message": coach_message}


@app.post("/api/session/{session_id}/end")
async def api_session_end(
    session_id: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    coach = active_coaches.get(session_id)
    meta = active_sessions[session_id]

    db_session = crud.get_session(db, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found in database")

    recent_sets = crud.get_recent_sets_for_exercise(
        db, meta["exercise"], session_limit=3, include_session_id=session_id
    )
    analysis = progression_engine.analyze(
        meta["exercise"],
        recent_sets,
        meta["goal"],
        meta.get("weight_kg"),
    )

    summary = _build_session_summary_from_db(db_session)
    summary["progression_analysis"] = analysis

    if coach is not None:
        try:
            progression_advice = await coach.get_progression_advice(summary)
        except Exception as exc:
            logger.exception("Progression advice failed: %s", exc)
            progression_advice = FALLBACK_MESSAGE
    else:
        progression_advice = FALLBACK_MESSAGE

    crud.complete_session(db, session_id, progression_advice)
    db.refresh(db_session)

    stats = _session_stats(db_session)
    session_pr = meta.get("session_had_pr", False)

    active_coaches.pop(session_id, None)
    active_sessions.pop(session_id, None)
    active_aggregators.pop(session_id, None)

    return {
        "progression_advice": progression_advice,
        "progression": analysis,
        "is_pr": session_pr,
        **stats,
    }


@app.get("/api/sessions")
async def api_get_sessions(db: DbSession = Depends(get_db)) -> dict[str, Any]:
    sessions = crud.get_all_sessions(db)
    return {"sessions": [crud.session_to_dict(s) for s in sessions]}


@app.get("/api/sessions/last/{exercise}")
async def api_get_last_session(
    exercise: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    last = crud.get_last_completed_session(db, exercise.strip().lower())
    if last is None:
        raise HTTPException(status_code=404, detail="No completed session found")
    return crud.session_to_dict(last)


@app.get("/api/stats/prs")
async def api_stats_prs(db: DbSession = Depends(get_db)) -> dict[str, Any]:
    prs = crud.get_prs(db)
    return {
        "prs": [
            {
                "exercise": pr.exercise,
                "weight_kg": pr.weight_kg,
                "reps": pr.reps,
                "e1rm": round(pr.e1rm, 1),
                "date": pr.date.isoformat(),
                "session_id": pr.session_id,
            }
            for pr in prs
        ]
    }


@app.get("/api/stats/history/{exercise}")
async def api_stats_history(
    exercise: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    sets = crud.get_exercise_history(db, exercise.strip().lower(), limit=20)
    return {
        "exercise": exercise,
        "sets": [
            {
                "date": s.session.date.isoformat() if s.session else None,
                "set_number": s.set_number,
                "weight_kg": s.weight_kg,
                "reps_completed": s.reps_completed,
                "e1rm": round(s.e1rm, 1),
                "form_score": round(s.form_score, 1),
                "rpe": s.rpe,
            }
            for s in sets
        ],
    }


@app.get("/api/stats/volume/{exercise}")
async def api_stats_volume(
    exercise: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    return {
        "exercise": exercise,
        "volume": crud.get_volume_by_date(db, exercise.strip().lower(), days=30),
    }


@app.get("/api/stats/form/{exercise}")
async def api_stats_form(
    exercise: str,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    return {
        "exercise": exercise,
        "trend": crud.get_form_score_trend(db, exercise.strip().lower(), limit=10),
    }


@app.get("/api/stats/bodyweight")
async def api_get_bodyweight(db: DbSession = Depends(get_db)) -> dict[str, Any]:
    logs = crud.get_bodyweight_history(db)
    return {
        "logs": [
            {"date": log.date.isoformat(), "weight_kg": log.weight_kg}
            for log in logs
        ]
    }


@app.post("/api/stats/bodyweight")
async def api_log_bodyweight(
    body: BodyweightBody,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    entry = crud.log_bodyweight(db, crud.DEFAULT_USER_ID, body.weight_kg)
    return {"date": entry.date.isoformat(), "weight_kg": entry.weight_kg}


@app.get("/api/dashboard")
async def api_dashboard(db: DbSession = Depends(get_db)) -> dict[str, Any]:
    return crud.get_dashboard_summary(db)


@app.websocket("/ws/session")
async def websocket_session(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket client connected")

    pose_detector: PoseDetector | None = None
    rep_counter: RepCounter | None = None
    active_exercise: BaseExercise | None = None
    angle_history: collections.deque[dict[str, float]] = collections.deque(
        maxlen=SMOOTHING_WINDOW
    )
    set_aggregator: SetAggregator | None = None
    configured = False
    default_phase = "standing"

    try:
        while True:
            message = await websocket.receive_text()

            if not configured:
                try:
                    config = json.loads(message)
                except json.JSONDecodeError:
                    await websocket.send_json(
                        {
                            "error": (
                                "First message must be JSON config, e.g. "
                                '{"exercise": "squat"}'
                            )
                        }
                    )
                    await websocket.close()
                    return

                exercise_name = config.get("exercise")
                if not exercise_name:
                    await websocket.send_json(
                        {"error": 'Config must include "exercise" field.'}
                    )
                    await websocket.close()
                    return

                try:
                    active_exercise = get_exercise(exercise_name)
                except ValueError:
                    await websocket.send_json(
                        {
                            "error": (
                                f"Unknown exercise: {exercise_name}. "
                                f"Valid: {VALID_EXERCISES}"
                            )
                        }
                    )
                    await websocket.close()
                    return

                linked_session_id = config.get("session_id")
                if linked_session_id and linked_session_id not in active_sessions:
                    await websocket.send_json(
                        {"error": f"Unknown session_id: {linked_session_id}"}
                    )
                    await websocket.close()
                    return

                if linked_session_id and linked_session_id in active_aggregators:
                    set_aggregator = active_aggregators[linked_session_id]
                else:
                    set_aggregator = SetAggregator()
                    if linked_session_id:
                        active_aggregators[linked_session_id] = set_aggregator

                if linked_session_id and linked_session_id in active_sessions:
                    active_sessions[linked_session_id]["exercise"] = exercise_name

                pose_detector = PoseDetector()
                rep_counter = RepCounter()
                rep_counter.set_exercise(active_exercise)
                set_aggregator.begin_set(0, 0, 0)
                default_phase = getattr(active_exercise, "phase", "standing")
                configured = True
                logger.info("WebSocket configured: %s", exercise_name)
                continue

            if pose_detector is None or rep_counter is None or active_exercise is None:
                await websocket.send_json({"error": "Session not configured."})
                await websocket.close()
                return

            if message == "RESET_SET":
                rep_counter.reset_set()
                if set_aggregator is not None:
                    set_aggregator.begin_set(
                        rep_counter.total_reps,
                        rep_counter.good_reps,
                        rep_counter.bad_reps,
                    )
                await websocket.send_json(
                    {"action": "set_reset", "total_reps": rep_counter.total_reps}
                )
                continue

            frame = _decode_frame(message)
            if frame is None:
                await websocket.send_json(
                    _empty_response(
                        "Invalid frame data.",
                        rep_counter,
                        active_exercise,
                        default_phase,
                    )
                )
                continue

            landmarks = pose_detector.process_frame(frame)

            if landmarks is None:
                await websocket.send_json(
                    _empty_response(
                        rep_counter=rep_counter,
                        exercise=active_exercise,
                        phase=default_phase,
                    )
                )
                continue

            raw_angles = _collect_raw_angles(landmarks)
            angles = _smooth_angles(angle_history, raw_angles)
            rep_data = rep_counter.process(landmarks, angles)
            default_phase = rep_data.get("phase", default_phase)

            if set_aggregator is not None:
                set_aggregator.record_frame(
                    rep_data.get("form_flags", []),
                    angles,
                )

            await websocket.send_json(
                _build_response(landmarks, rep_data, angles, active_exercise)
            )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.exception("WebSocket session error: %s", exc)
    finally:
        if pose_detector is not None:
            pose_detector.close()
        logger.info("Session cleaned up")
