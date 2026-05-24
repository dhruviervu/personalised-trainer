"""
Database CRUD operations for sessions, sets, PRs, and stats.
"""

import datetime
from collections import defaultdict
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session as DbSession, joinedload

from database.models import BodyweightLog, PersonalRecord, Session, SetLog, User

DEFAULT_USER_ID = "default"


def _ensure_default_user(db: DbSession) -> User:
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    if user is None:
        user = User(id=DEFAULT_USER_ID, name="Athlete", goal="strength")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def calculate_e1rm(weight_kg: float, reps: int) -> float:
    """Epley formula: estimated 1RM."""
    if reps <= 0:
        return float(weight_kg)
    return float(weight_kg * (1 + reps / 30))


def calculate_form_score(good_reps: int, reps_completed: int) -> float:
    if reps_completed <= 0:
        return 0.0
    return float((good_reps / reps_completed) * 100)


# --- Sessions ---


def create_session(
    db: DbSession,
    exercise: str,
    goal: str,
    user_id: str = DEFAULT_USER_ID,
) -> Session:
    _ensure_default_user(db)
    session = Session(
        user_id=user_id,
        exercise=exercise,
        goal=goal.lower(),
        completed=False,
        total_volume_kg=0.0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def complete_session(
    db: DbSession,
    session_id: str,
    progression_advice: str,
) -> Session | None:
    session = db.query(Session).filter(Session.id == session_id).first()
    if session is None:
        return None

    session.completed = True
    session.progression_advice = progression_advice

    sets = db.query(SetLog).filter(SetLog.session_id == session_id).all()
    session.total_volume_kg = sum(s.weight_kg * s.reps_completed for s in sets)

    db.commit()
    db.refresh(session)
    return session


def get_session(db: DbSession, session_id: str) -> Session | None:
    return (
        db.query(Session)
        .options(joinedload(Session.sets))
        .filter(Session.id == session_id)
        .first()
    )


def get_sessions_for_exercise(
    db: DbSession,
    exercise: str,
    limit: int = 10,
) -> list[Session]:
    return (
        db.query(Session)
        .options(joinedload(Session.sets))
        .filter(Session.exercise == exercise, Session.completed.is_(True))
        .order_by(desc(Session.date))
        .limit(limit)
        .all()
    )


def get_all_sessions(db: DbSession, limit: int = 50) -> list[Session]:
    return (
        db.query(Session)
        .options(joinedload(Session.sets))
        .order_by(desc(Session.date))
        .limit(limit)
        .all()
    )


def get_last_completed_session(db: DbSession, exercise: str) -> Session | None:
    return (
        db.query(Session)
        .options(joinedload(Session.sets))
        .filter(Session.exercise == exercise, Session.completed.is_(True))
        .order_by(desc(Session.date))
        .first()
    )


# --- Sets ---


def log_set(
    db: DbSession,
    session_id: str,
    set_data: dict[str, Any],
    rpe: float | None,
    coach_feedback: str,
) -> SetLog | None:
    session = db.query(Session).filter(Session.id == session_id).first()
    if session is None:
        return None

    reps = int(set_data.get("reps_completed", 0))
    good = int(set_data.get("good_reps", 0))
    bad = int(set_data.get("bad_reps", 0))
    weight = float(set_data.get("weight_kg", 0))
    set_number = int(set_data.get("set_number", 1))

    form_score = calculate_form_score(good, reps)
    e1rm = calculate_e1rm(weight, reps)

    avg_angles = dict(set_data.get("avg_angles") or {})
    exercise_name = set_data.get("exercise")
    if exercise_name:
        avg_angles["exercise"] = exercise_name

    set_log = SetLog(
        session_id=session_id,
        set_number=set_number,
        weight_kg=weight,
        reps_completed=reps,
        good_reps=good,
        bad_reps=bad,
        rpe=rpe,
        form_flags=set_data.get("form_flags") or [],
        avg_angles=avg_angles,
        form_score=form_score,
        e1rm=e1rm,
        coach_feedback=coach_feedback,
    )
    db.add(set_log)
    db.flush()

    all_sets = db.query(SetLog).filter(SetLog.session_id == session_id).all()
    session.total_volume_kg = sum(s.weight_kg * s.reps_completed for s in all_sets)

    db.commit()
    db.refresh(set_log)
    return set_log


def update_last_set_rpe(db: DbSession, session_id: str, rpe: float) -> SetLog | None:
    last_set = (
        db.query(SetLog)
        .filter(SetLog.session_id == session_id)
        .order_by(desc(SetLog.set_number))
        .first()
    )
    if last_set is None:
        return None
    last_set.rpe = float(rpe)
    db.commit()
    db.refresh(last_set)
    return last_set


def get_sets_for_session(db: DbSession, session_id: str) -> list[SetLog]:
    return (
        db.query(SetLog)
        .filter(SetLog.session_id == session_id)
        .order_by(SetLog.set_number)
        .all()
    )


# --- PRs ---


def check_and_update_pr(
    db: DbSession,
    user_id: str,
    exercise: str,
    weight_kg: float,
    reps: int,
    e1rm: float,
    session_id: str,
) -> tuple[bool, PersonalRecord | None]:
    _ensure_default_user(db)

    existing = (
        db.query(PersonalRecord)
        .filter(PersonalRecord.user_id == user_id, PersonalRecord.exercise == exercise)
        .order_by(desc(PersonalRecord.e1rm))
        .first()
    )

    is_new = existing is None or e1rm > existing.e1rm

    if not is_new:
        return False, existing

    pr = PersonalRecord(
        user_id=user_id,
        exercise=exercise,
        weight_kg=weight_kg,
        reps=reps,
        e1rm=e1rm,
        session_id=session_id,
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return True, pr


# --- Stats ---


def get_exercise_history(db: DbSession, exercise: str, limit: int = 20) -> list[SetLog]:
    return (
        db.query(SetLog)
        .join(Session, SetLog.session_id == Session.id)
        .options(joinedload(SetLog.session))
        .filter(Session.exercise == exercise)
        .order_by(desc(Session.date), desc(SetLog.set_number))
        .limit(limit)
        .all()
    )


def get_recent_sets_for_exercise(
    db: DbSession,
    exercise: str,
    session_limit: int = 3,
    include_session_id: str | None = None,
) -> list[SetLog]:
    """Sets from the last N completed sessions, optionally including an active session."""
    sessions = get_sessions_for_exercise(db, exercise, limit=session_limit)
    session_ids = [s.id for s in sessions]

    if include_session_id and include_session_id not in session_ids:
        session_ids.insert(0, include_session_id)

    if not session_ids:
        return []

    return (
        db.query(SetLog)
        .filter(SetLog.session_id.in_(session_ids))
        .order_by(desc(SetLog.id))
        .all()
    )


def get_prs(db: DbSession, user_id: str = DEFAULT_USER_ID) -> list[PersonalRecord]:
    """Best e1RM PR per exercise."""
    all_prs = (
        db.query(PersonalRecord)
        .filter(PersonalRecord.user_id == user_id)
        .order_by(desc(PersonalRecord.e1rm))
        .all()
    )
    best_by_exercise: dict[str, PersonalRecord] = {}
    for pr in all_prs:
        if pr.exercise not in best_by_exercise or pr.e1rm > best_by_exercise[pr.exercise].e1rm:
            best_by_exercise[pr.exercise] = pr
    return sorted(best_by_exercise.values(), key=lambda p: p.exercise)


def get_volume_by_date(
    db: DbSession,
    exercise: str,
    days: int = 30,
) -> list[dict[str, Any]]:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    sets = (
        db.query(SetLog, Session)
        .join(Session, SetLog.session_id == Session.id)
        .filter(Session.exercise == exercise, Session.date >= cutoff)
        .all()
    )

    volume_by_date: dict[str, float] = defaultdict(float)
    for set_log, session in sets:
        day_key = session.date.strftime("%Y-%m-%d")
        volume_by_date[day_key] += set_log.weight_kg * set_log.reps_completed

    return [
        {"date": date_key, "total_volume": round(vol, 1)}
        for date_key, vol in sorted(volume_by_date.items())
    ]


def get_form_score_trend(
    db: DbSession,
    exercise: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    sessions = get_sessions_for_exercise(db, exercise, limit=limit)
    trend: list[dict[str, Any]] = []

    for session in reversed(sessions):
        if not session.sets:
            continue
        scores = [s.form_score for s in session.sets if s.form_score is not None]
        if not scores:
            continue
        trend.append(
            {
                "session_date": session.date.strftime("%Y-%m-%d"),
                "avg_form_score": round(sum(scores) / len(scores), 1),
            }
        )
    return trend


def log_bodyweight(
    db: DbSession,
    user_id: str,
    weight_kg: float,
) -> BodyweightLog:
    _ensure_default_user(db)
    entry = BodyweightLog(user_id=user_id, weight_kg=weight_kg)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_bodyweight_history(
    db: DbSession,
    user_id: str = DEFAULT_USER_ID,
    days: int = 90,
) -> list[BodyweightLog]:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    return (
        db.query(BodyweightLog)
        .filter(BodyweightLog.user_id == user_id, BodyweightLog.date >= cutoff)
        .order_by(BodyweightLog.date)
        .all()
    )


def compute_streak(db: DbSession, user_id: str = DEFAULT_USER_ID) -> int:
    """Consecutive calendar days with at least one completed session."""
    sessions = (
        db.query(Session)
        .filter(Session.user_id == user_id, Session.completed.is_(True))
        .all()
    )
    if not sessions:
        return 0

    days = sorted({s.date.date() for s in sessions}, reverse=True)
    today = datetime.datetime.utcnow().date()

    if days[0] < today - datetime.timedelta(days=1):
        return 0

    streak = 1
    for i in range(1, len(days)):
        if (days[i - 1] - days[i]).days == 1:
            streak += 1
        else:
            break
    return streak


def get_dashboard_summary(db: DbSession, user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    sessions = (
        db.query(Session)
        .options(joinedload(Session.sets))
        .filter(Session.user_id == user_id, Session.completed.is_(True))
        .order_by(desc(Session.date))
        .all()
    )

    total_volume = sum(s.total_volume_kg or 0 for s in sessions)
    prs = get_prs(db, user_id)

    recent = []
    for s in sessions[:5]:
        top_set = max(s.sets, key=lambda x: x.weight_kg * x.reps_completed, default=None) if s.sets else None
        scores = [x.form_score for x in s.sets if x.form_score is not None]
        recent.append(
            {
                "session_id": s.id,
                "exercise": s.exercise,
                "date": s.date.isoformat(),
                "sets_count": len(s.sets),
                "total_reps": sum(x.reps_completed for x in s.sets),
                "top_set_weight": top_set.weight_kg if top_set else 0,
                "top_set_reps": top_set.reps_completed if top_set else 0,
                "avg_form_score": round(sum(scores) / len(scores), 1) if scores else 0,
            }
        )

    return {
        "total_sessions": len(sessions),
        "total_volume_kg": round(total_volume, 1),
        "prs": [
            {
                "exercise": pr.exercise,
                "weight_kg": pr.weight_kg,
                "reps": pr.reps,
                "e1rm": round(pr.e1rm, 1),
                "date": pr.date.isoformat(),
            }
            for pr in prs
        ],
        "recent_sessions": recent,
        "streak": compute_streak(db, user_id),
    }


def session_to_dict(session: Session) -> dict[str, Any]:
    return {
        "session_id": session.id,
        "exercise": session.exercise,
        "goal": session.goal,
        "date": session.date.isoformat(),
        "completed": session.completed,
        "progression_advice": session.progression_advice,
        "total_volume_kg": session.total_volume_kg,
        "sets": [
            {
                "set_number": s.set_number,
                "weight_kg": s.weight_kg,
                "reps_completed": s.reps_completed,
                "good_reps": s.good_reps,
                "bad_reps": s.bad_reps,
                "rpe": s.rpe,
                "form_flags": s.form_flags,
                "avg_angles": s.avg_angles,
                "form_score": s.form_score,
                "e1rm": s.e1rm,
                "coach_feedback": s.coach_feedback,
            }
            for s in session.sets
        ],
    }
