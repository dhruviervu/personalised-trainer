import { useMemo, useState } from 'react';
import { startSession } from '../api/sessionApi';

const GOALS = ['Strength', 'Hypertrophy', 'Endurance', 'Cut'];

/**
 * Post-exercise setup: goal, weight, and coach session start.
 */
export default function SessionSetup({
  exercise,
  exerciseLabel,
  onSessionReady,
  onBack,
  isNewSession = true,
  existingGoal = 'Strength',
  existingWeightKg = 0,
  existingSessionId = null,
  existingOpeningMessage = '',
}) {
  const [goal, setGoal] = useState(existingGoal);
  const [weightKg, setWeightKg] = useState(existingWeightKg ? String(existingWeightKg) : '');
  const defaultBodyweight = useMemo(
    () => ['pull_up', 'squat'].includes(exercise),
    [exercise]
  );
  const [isBodyweight, setIsBodyweight] = useState(defaultBodyweight);
  const [additionalLoadKg, setAdditionalLoadKg] = useState('0');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [openingMessage, setOpeningMessage] = useState(null);
  const [pendingSession, setPendingSession] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    const parsedWeight = parseFloat(weightKg || '0');
    const parsedAdditionalLoad = parseFloat(additionalLoadKg || '0');
    const weight = isBodyweight ? Math.max(0, parsedAdditionalLoad || 0) : parsedWeight;

    if (!isBodyweight && (!weight || weight <= 0)) {
      setError('Enter a valid starting weight in kg.');
      return;
    }

    if (!isNewSession) {
      setPendingSession({
        sessionId: existingSessionId,
        goal,
        weightKg: weight,
      });
      setOpeningMessage(existingOpeningMessage || null);
      return;
    }

    setLoading(true);
    try {
      const result = await startSession(exercise, goal, weight);
      setOpeningMessage(result.opening_message);
      setPendingSession({
        sessionId: result.session_id,
        goal,
        weightKg: weight,
      });
    } catch (err) {
      setError(err.message || 'Failed to start session.');
    } finally {
      setLoading(false);
    }
  };

  const handleBeginWorkout = () => {
    if (!pendingSession) {
      return;
    }
    onSessionReady({
      sessionId: pendingSession.sessionId,
      goal: pendingSession.goal,
      weightKg: pendingSession.weightKg,
      openingMessage,
    });
  };

  return (
    <div className="session-setup">
      <button type="button" className="session-setup__back" onClick={onBack}>
        ← Back
      </button>

      <h2 className="session-setup__title">{exerciseLabel} session</h2>
      <p className="session-setup__subtitle">
        {isNewSession ? 'Set your goal and working weight' : `Adding ${exerciseLabel} to current session`}
      </p>

      <form className="session-setup__form" onSubmit={handleSubmit}>
        {isNewSession && (
          <fieldset className="session-setup__field">
            <legend className="session-setup__label">Training goal</legend>
            <div className="goal-group">
              {GOALS.map((g) => (
                <button
                  key={g}
                  type="button"
                  className={`goal-btn ${goal === g ? 'goal-btn--active' : ''}`}
                  onClick={() => setGoal(g)}
                >
                  {g}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        <label className="session-setup__field">
          <span className="session-setup__label">Bodyweight exercise</span>
          <input
            type="checkbox"
            checked={isBodyweight}
            onChange={(e) => setIsBodyweight(e.target.checked)}
          />
        </label>

        {isBodyweight ? (
          <div className="session-setup__field">
            <p className="session-setup__subtitle" style={{ textAlign: 'left', margin: 0 }}>
              Bodyweight — add load if applicable (e.g. +10kg vest)
            </p>
            <label className="session-setup__field">
              <span className="session-setup__label">Additional load (kg)</span>
              <input
                type="number"
                className="session-setup__input"
                min="0"
                step="0.5"
                placeholder="e.g. 10"
                value={additionalLoadKg}
                onChange={(e) => setAdditionalLoadKg(e.target.value)}
              />
            </label>
          </div>
        ) : (
          <label className="session-setup__field">
            <span className="session-setup__label">Starting weight (kg)</span>
            <input
              type="number"
              className="session-setup__input"
              min="1"
              step="0.5"
              placeholder="e.g. 100"
              value={weightKg}
              onChange={(e) => setWeightKg(e.target.value)}
              required
            />
          </label>
        )}

        {error && <p className="session-setup__error">{error}</p>}

        {!pendingSession ? (
          <button type="submit" className="session-setup__submit" disabled={loading}>
            {loading ? 'Starting coach…' : isNewSession ? 'Start Session' : 'Continue'}
          </button>
        ) : (
          <div className="session-setup__coach-preview">
            <p className="session-setup__coach-label">Your coach says:</p>
            <p className="session-setup__coach-message">{openingMessage}</p>
            <button type="button" className="session-setup__submit" onClick={handleBeginWorkout}>
              Begin Workout
            </button>
          </div>
        )}
      </form>
    </div>
  );
}
