/**
 * Real-time coaching feedback and form flag badges.
 */

function feedbackTone(feedback, formFlags) {
  const errorFlags = [
    'knees_caving',
    'back_rounding',
    'flared_elbows',
    'forward_lean',
    'bending_knees',
    'no_chin_over_bar',
  ];
  if (formFlags?.some((f) => errorFlags.includes(f))) {
    return 'error';
  }
  if (formFlags?.includes('good_rep') || /good rep|good lift|locked out|full rep|full lockout/i.test(feedback || '')) {
    return 'success';
  }
  if (
    formFlags?.some((f) =>
      ['insufficient_depth', 'shallow_hinge', 'no_lockout'].includes(f)
    ) ||
    /go deeper|didn't hit depth|parallel|hinge deeper|pull higher/i.test(feedback || '')
  ) {
    return 'warning';
  }
  if (/knees out|rounding|tuck your elbows|leaning back/i.test(feedback || '')) {
    return 'error';
  }
  return 'neutral';
}

const FLAG_LABELS = {
  knees_caving: 'Knees caving',
  insufficient_depth: 'Insufficient depth',
  good_rep: 'Good rep',
  back_rounding: 'Back rounding',
  shallow_hinge: 'Shallow hinge',
  flared_elbows: 'Flared elbows',
  no_lockout: 'No lockout',
  forward_lean: 'Forward lean',
  bending_knees: 'Bending knees',
  no_chin_over_bar: 'Chin not over bar',
};

export default function FormFeedback({ feedback, formFlags, phase }) {
  const tone = feedbackTone(feedback, formFlags);

  return (
    <div className={`form-feedback form-feedback--${tone}`}>
      <p className="form-feedback__message">{feedback || 'Waiting for pose…'}</p>
      {phase && <span className="form-feedback__phase-hint">{phase}</span>}
      {formFlags && formFlags.length > 0 && (
        <div className="form-feedback__badges">
          {formFlags.map((flag) => (
            <span key={flag} className={`form-badge form-badge--${flag}`}>
              {FLAG_LABELS[flag] || flag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
