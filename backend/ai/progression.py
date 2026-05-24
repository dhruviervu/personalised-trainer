"""
Rule-based progression engine — recommends weight and focus for next session.
"""

from typing import Any

from database.models import SetLog

DEFAULT_USER_ID = "default"
WEIGHT_INCREMENT = 2.5


def _round_weight(weight: float) -> float:
    """Round to nearest 2.5 kg."""
    return round(weight / WEIGHT_INCREMENT) * WEIGHT_INCREMENT


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


class ProgressionEngine:
    """Analyses recent training data and recommends next-session load."""

    def analyze(
        self,
        exercise: str,
        recent_sets: list[SetLog],
        goal: str,
        current_weight_kg: float | None = None,
    ) -> dict[str, Any]:
        """
        Return progression recommendation based on RPE, form, and training goal.

        recent_sets: sets from the last ~3 sessions for this exercise (newest first).
        """
        goal_key = (goal or "strength").lower()
        base_weight = current_weight_kg or 0.0
        if base_weight <= 0 and recent_sets:
            base_weight = recent_sets[0].weight_kg

        if not recent_sets:
            return {
                "recommendation": "maintain",
                "next_weight_kg": _round_weight(base_weight) if base_weight else 0.0,
                "reasoning": "No prior data for this lift — establish a baseline this session.",
                "next_session_notes": "Focus on consistent reps and logging RPE each set.",
            }

        # Group sets by session_id (preserve order via recent_sets list)
        sessions_map: dict[str, list[SetLog]] = {}
        session_order: list[str] = []
        for s in recent_sets:
            if s.session_id not in sessions_map:
                sessions_map[s.session_id] = []
                session_order.append(s.session_id)
            sessions_map[s.session_id].append(s)

        last_session_sets = sessions_map.get(session_order[0], []) if session_order else []
        last_session_form = _avg([s.form_score for s in last_session_sets if s.form_score is not None])

        # RPE per session (avg RPE of sets with RPE logged)
        session_rpes: list[float] = []
        for sid in session_order[:3]:
            rpes = [s.rpe for s in sessions_map[sid] if s.rpe is not None]
            avg_rpe = _avg(rpes)
            if avg_rpe is not None:
                session_rpes.append(avg_rpe)

        avg_rpe_last_two = _avg(session_rpes[:2]) if session_rpes else None

        # Missed reps heuristic: bad_reps > 0 or low form on last session
        missed_reps = any(
            s.bad_reps > 0 or (s.reps_completed > 0 and s.good_reps < s.reps_completed * 0.8)
            for s in last_session_sets
        )

        recommendation = "maintain"
        reasoning_parts: list[str] = []

        if last_session_form is not None and last_session_form < 70:
            recommendation = "form_focus"
            reasoning_parts.append(
                f"Form score averaged {last_session_form:.0f}% last session — clean up technique before adding load."
            )
        elif avg_rpe_last_two is not None and avg_rpe_last_two > 9:
            recommendation = "deload"
            reasoning_parts.append(
                f"Average RPE {avg_rpe_last_two:.1f} across recent sessions — you're grinding too hard."
            )
        elif avg_rpe_last_two is not None and avg_rpe_last_two < 7:
            recommendation = "progress"
            reasoning_parts.append(
                f"Average RPE {avg_rpe_last_two:.1f} — you have room to push weight up."
            )
        elif missed_reps:
            recommendation = "maintain"
            reasoning_parts.append("Rep quality dropped last session — hold weight and nail your sets.")
        else:
            recommendation = "maintain"
            reasoning_parts.append("Training looks stable — small progress or maintain is appropriate.")

        # Goal modifiers
        if goal_key == "strength" and recommendation == "progress":
            reasoning_parts.append("Strength goal: prioritise heavier sets in the 3–5 rep range.")
        elif goal_key == "hypertrophy":
            if recommendation == "progress":
                reasoning_parts.append("Hypertrophy goal: add weight or an extra set at 8–12 reps.")
            else:
                reasoning_parts.append("Hypertrophy goal: chase volume in the 8–12 rep range.")
        elif goal_key == "cut":
            if recommendation == "progress":
                recommendation = "maintain"
            reasoning_parts.append("Cut phase: maintain strength, avoid chasing volume spikes.")
        elif goal_key == "endurance":
            if recommendation == "progress":
                reasoning_parts.append("Endurance goal: add reps before load where possible.")
            else:
                reasoning_parts.append("Endurance goal: build rep capacity at moderate loads.")

        # Next weight
        next_weight = base_weight
        if recommendation == "progress":
            next_weight = base_weight + WEIGHT_INCREMENT
        elif recommendation == "deload":
            next_weight = max(WEIGHT_INCREMENT, base_weight - WEIGHT_INCREMENT * 2)
        elif recommendation == "form_focus":
            next_weight = base_weight
        else:
            next_weight = base_weight

        next_weight = _round_weight(next_weight)

        notes_map = {
            "progress": f"Try {next_weight}kg next session and stay in your target rep range.",
            "maintain": f"Stay at {next_weight}kg and aim for cleaner reps than last time.",
            "deload": f"Drop to {next_weight}kg, rebuild bar speed, then ramp back up.",
            "form_focus": f"Keep {next_weight}kg but slow down — fix form before adding load.",
        }

        return {
            "recommendation": recommendation,
            "next_weight_kg": next_weight,
            "reasoning": " ".join(reasoning_parts),
            "next_session_notes": notes_map.get(recommendation, notes_map["maintain"]),
        }
