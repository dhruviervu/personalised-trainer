const EXERCISE_LABELS = {
  squat: 'Squat',
  deadlift: 'Deadlift',
  bench_press: 'Bench Press',
  overhead_press: 'Overhead Press',
  romanian_deadlift: 'Romanian Deadlift',
  pull_up: 'Pull-up',
};

/**
 * End-of-session modal with stats and progression advice.
 */
export default function SessionSummary({
  summary,
  onNewSession,
  onViewDashboard,
}) {
  if (!summary) {
    return null;
  }

  const {
    exercise,
    exercises = [],
    totalSets,
    totalReps,
    goodRepPercent,
    formScorePercent,
    topSet,
    sessionE1rm,
    isPr,
    progressionAdvice,
    progression,
    goal,
    weightKg,
    totalVolumeKg,
  } = summary;

  const multiExercise = exercises.length > 1;
  const label = multiExercise
    ? 'Multi-exercise session'
    : EXERCISE_LABELS[exercise] || EXERCISE_LABELS[exercises[0]?.exercise] || exercise;
  const displayFormScore = formScorePercent ?? goodRepPercent;

  return (
    <div className="session-summary-backdrop">
      <div className="session-summary">
        <h2 className="session-summary__title">Session complete</h2>
        <p className="session-summary__exercise">{label}</p>

        {multiExercise && (
          <ul className="session-summary__exercise-list">
            {exercises.map((item) => (
              <li key={item.exercise}>
                <strong>{EXERCISE_LABELS[item.exercise] || item.exercise}</strong>
                {' — '}
                {item.sets} set{item.sets !== 1 ? 's' : ''}, {item.reps} reps
                {item.volume_kg > 0 ? `, ${item.volume_kg} kg volume` : ''}
                {item.form_score_percent != null
                  ? `, ${item.form_score_percent}% form`
                  : ''}
              </li>
            ))}
          </ul>
        )}

        {isPr && (
          <div className="session-summary__pr-badge">🏆 Personal record this session</div>
        )}

        <dl className="session-summary__stats">
          <div>
            <dt>Goal</dt>
            <dd>{goal}</dd>
          </div>
          <div>
            <dt>Working weight</dt>
            <dd>{weightKg} kg</dd>
          </div>
          <div>
            <dt>Sets</dt>
            <dd>{totalSets}</dd>
          </div>
          <div>
            <dt>Total reps</dt>
            <dd>{totalReps}</dd>
          </div>
          <div>
            <dt>Form score</dt>
            <dd>{displayFormScore}%</dd>
          </div>
          {topSet && (
            <div>
              <dt>Top set</dt>
              <dd>
                {topSet.weight_kg}kg × {topSet.reps}
                {topSet.exercise && multiExercise
                  ? ` (${EXERCISE_LABELS[topSet.exercise] || topSet.exercise})`
                  : ''}
              </dd>
            </div>
          )}
          {sessionE1rm > 0 && (
            <div>
              <dt>Session e1RM</dt>
              <dd>{sessionE1rm} kg</dd>
            </div>
          )}
          {totalVolumeKg > 0 && (
            <div>
              <dt>Volume</dt>
              <dd>{totalVolumeKg} kg</dd>
            </div>
          )}
        </dl>

        {progression?.next_weight_kg != null && (
          <p className="session-summary__next-weight">
            Suggested next session: <strong>{progression.next_weight_kg}kg</strong>
            {' '}({progression.recommendation?.replace('_', ' ')})
          </p>
        )}

        <div className="session-summary__advice">
          <h3>Coach — next session</h3>
          <p>{progressionAdvice}</p>
        </div>

        <div className="session-summary__actions">
          <button type="button" className="session-summary__btn" onClick={onNewSession}>
            Start New Session
          </button>
          {onViewDashboard && (
            <button
              type="button"
              className="session-summary__btn session-summary__btn--secondary"
              onClick={onViewDashboard}
            >
              View Dashboard
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
