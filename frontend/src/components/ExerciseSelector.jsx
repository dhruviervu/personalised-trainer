const EXERCISES = [
  { id: 'squat', name: 'Squat', camera: 'front' },
  { id: 'deadlift', name: 'Deadlift', camera: 'side' },
  { id: 'bench_press', name: 'Bench Press', camera: 'side' },
  { id: 'overhead_press', name: 'Overhead Press', camera: 'front' },
  { id: 'romanian_deadlift', name: 'Romanian Deadlift', camera: 'side' },
  { id: 'pull_up', name: 'Pull-up', camera: 'front' },
];

function cameraLabel(angle) {
  return angle === 'side' ? '📷 Side view' : '📷 Front view';
}

/**
 * Exercise picker grid shown before the camera session starts.
 */
export default function ExerciseSelector({ onSelect }) {
  return (
    <div className="exercise-selector">
      <h2 className="exercise-selector__title">Choose an exercise</h2>
      <p className="exercise-selector__subtitle">
        Select a movement to start tracking reps and form
      </p>
      <div className="exercise-selector__grid">
        {EXERCISES.map((exercise) => (
          <button
            key={exercise.id}
            type="button"
            className="exercise-card"
            onClick={() => onSelect(exercise.id)}
          >
            <span className="exercise-card__name">{exercise.name}</span>
            <span className="exercise-card__camera">{cameraLabel(exercise.camera)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
