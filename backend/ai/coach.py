"""
Groq-powered AI strength coach for post-set feedback and progression.
"""

import logging
import os
import re
from typing import Any

from groq import AsyncGroq

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert strength and conditioning coach with 15 years of experience. You are direct, knowledgeable, and genuinely helpful. You do not give generic advice — every response is specific to what the athlete just did.

Your job after each set:
1. Acknowledge what you observed from the form data
2. Ask for their RPE (Rate of Perceived Exertion) on a scale of 1-10 if you don't have it yet
3. Once you have RPE, give one specific actionable coaching cue for next set
4. Log the set and decide: progress weight, maintain, or address form first

Keep responses conversational and under 3 sentences unless explaining something technical. Do not use bullet points in responses — talk like a coach, not a textbook. Never say "Great job!" or "Awesome!" — be real.
When starting a session, greet the athlete warmly and briefly. Do not ask for their weight, RPE scale explanations, or technical details upfront. Simply say you will be watching their form, ask what they are hoping to get out of this session in plain language, and let them know they can chat with you before starting. Keep it to 2 sentences maximum. Never use the term RPE without immediately explaining it in plain English in parentheses."""

FALLBACK_MESSAGE = "Coach unavailable — log your RPE manually"

MODEL = "llama-3.3-70b-versatile"


def _format_angles_human(exercise: str, avg_angles: dict[str, float]) -> str:
    """Translate raw angle dicts into coach-readable phrases."""
    if not avg_angles:
        return "no angle data captured"

    parts: list[str] = []
    exercise_key = exercise.lower().replace("-", "_")

    if exercise_key in ("squat",):
        lk = avg_angles.get("left_knee")
        rk = avg_angles.get("right_knee")
        if lk and rk:
            parts.append(f"avg knee depth {((lk + rk) / 2):.0f}°")
        back = avg_angles.get("back_angle")
        if back:
            parts.append(f"torso lean {back:.0f}° from vertical")

    elif exercise_key in ("deadlift", "romanian_deadlift"):
        hinge = avg_angles.get("hip_hinge") or (
            (avg_angles.get("left_hip", 0) + avg_angles.get("right_hip", 0)) / 2
        )
        if hinge:
            parts.append(f"avg hip hinge {hinge:.0f}°")
        back = avg_angles.get("back_angle")
        if back:
            parts.append(f"back angle {back:.0f}° from vertical")
        if exercise_key == "romanian_deadlift":
            lk = avg_angles.get("left_knee")
            rk = avg_angles.get("right_knee")
            if lk and rk:
                parts.append(f"knee angle held around {((lk + rk) / 2):.0f}°")

    elif exercise_key in ("bench_press", "overhead_press", "pull_up"):
        le = avg_angles.get("left_elbow")
        re = avg_angles.get("right_elbow")
        if le and re:
            label = "lockout" if exercise_key == "overhead_press" else "elbow flexion"
            parts.append(f"avg {label} {((le + re) / 2):.0f}°")
        if exercise_key == "overhead_press":
            back = avg_angles.get("back_angle")
            if back:
                parts.append(f"lean back {back:.0f}°")

    else:
        for key, value in sorted(avg_angles.items()):
            if key.endswith("_x") or key.endswith("_y"):
                continue
            readable = key.replace("_", " ")
            parts.append(f"{readable} {value:.0f}°")

    return ", ".join(parts) if parts else "limited angle data"


def _build_set_context_message(set_data: dict[str, Any]) -> str:
    """Format set completion as a user message for the coach."""
    exercise = set_data.get("exercise", "exercise")
    set_number = set_data.get("set_number", 1)
    reps = set_data.get("reps_completed", 0)
    weight = set_data.get("weight_kg", 0)
    good = set_data.get("good_reps", 0)
    flags = set_data.get("form_flags") or []
    flags_text = ", ".join(flags) if flags else "none"
    angles_text = _format_angles_human(exercise, set_data.get("avg_angles") or {})

    return (
        f"Set {set_number} complete: {reps} reps at {weight}kg. "
        f"Good reps: {good}, form issues: {flags_text}. "
        f"Key angles — {angles_text}."
    )


class GroqCoach:
    """Maintains per-session conversation with Groq and generates coaching text."""

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not set — coach will use fallback messages")
        self._client = AsyncGroq(api_key=api_key) if api_key else None
        self._history: list[dict[str, str]] = []
        self._exercise: str = ""
        self._goal: str = ""
        self._has_rpe: bool = False

    def _reset_history(self) -> None:
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]

    async def _chat(self, user_content: str) -> str:
        """Send a user turn and return the assistant reply."""
        if not self._client:
            return FALLBACK_MESSAGE

        self._history.append({"role": "user", "content": user_content})

        try:
            response = await self._client.chat.completions.create(
                model=MODEL,
                messages=self._history,
                temperature=0.7,
                max_tokens=300,
            )
            reply = response.choices[0].message.content or FALLBACK_MESSAGE
            self._history.append({"role": "assistant", "content": reply})
            return reply.strip()
        except Exception as exc:
            logger.exception("Groq API call failed: %s", exc)
            return FALLBACK_MESSAGE

    async def start_session(self, exercise: str, goal: str) -> str:
        """Reset conversation and return the coach's opening message."""
        self._reset_history()
        self._exercise = exercise
        self._goal = goal
        self._has_rpe = False

        opening_context = f"I'm about to start a {exercise} session. My goal is {goal}."
        return await self._chat(opening_context)

    async def post_set_message(
        self,
        set_data: dict[str, Any],
        user_message: str | None = None,
        extra_context: str | None = None,
    ) -> str:
        """
        After a set: inject set context, or continue conversation with user reply.

        When user_message is None, sends structured set data as context.
        """
        if user_message is None:
            context = _build_set_context_message(set_data)
            if extra_context:
                context = f"{context}\n\n{extra_context}"
            return await self._chat(context)

        # Detect RPE in user message for conversation state
        rpe_match = re.search(r"\b(?:rpe\s*)?([1-9]|10)\b", user_message.lower())
        if rpe_match:
            self._has_rpe = True

        return await self._chat(user_message)

    async def get_progression_advice(self, session_summary: dict[str, Any]) -> str:
        """Generate end-of-session progression guidance."""
        exercise = session_summary.get("exercise", "session")
        goal = session_summary.get("goal", "")
        total_sets = session_summary.get("total_sets", 0)
        rpe_trend = session_summary.get("rpe_trend", [])
        flag_freq = session_summary.get("form_flag_frequency", {})
        sets_detail = session_summary.get("sets", [])

        flags_text = (
            ", ".join(f"{k} ({v}x)" for k, v in flag_freq.items())
            if flag_freq
            else "none recurring"
        )
        rpe_text = ", ".join(str(r) for r in rpe_trend) if rpe_trend else "not recorded"

        progression = session_summary.get("progression_analysis", {})
        progression_text = ""
        if progression:
            progression_text = (
                f" Progression engine recommends: {progression.get('recommendation')} "
                f"at {progression.get('next_weight_kg')}kg. "
                f"Reasoning: {progression.get('reasoning')} "
                f"Notes: {progression.get('next_session_notes')}"
            )

        summary_prompt = (
            f"Session complete for {exercise}. Goal was {goal}. "
            f"{total_sets} sets logged. RPE trend: {rpe_text}. "
            f"Recurring form issues: {flags_text}. "
            f"Set breakdown: {sets_detail}.{progression_text} "
            "Give concise advice for next session: progress weight, hold, or fix form first."
        )

        if not self._client:
            return FALLBACK_MESSAGE

        self._history.append({"role": "user", "content": summary_prompt})
        try:
            response = await self._client.chat.completions.create(
                model=MODEL,
                messages=self._history,
                temperature=0.7,
                max_tokens=400,
            )
            reply = response.choices[0].message.content or FALLBACK_MESSAGE
            self._history.append({"role": "assistant", "content": reply})
            return reply.strip()
        except Exception as exc:
            logger.exception("Groq progression advice failed: %s", exc)
            return FALLBACK_MESSAGE


def parse_rpe_from_message(message: str) -> int | None:
    """Extract RPE 1–10 from a user chat message."""
    match = re.search(r"\b(?:rpe\s*)?([1-9]|10)\b", message.lower())
    if match:
        return int(match.group(1))
    return None
