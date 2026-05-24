import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  fetchDashboard,
  fetchExerciseHistory,
  fetchExerciseVolume,
  fetchFormTrend,
} from '../api/statsApi';

const EXERCISE_LABELS = {
  squat: 'Squat',
  deadlift: 'Deadlift',
  bench_press: 'Bench Press',
  overhead_press: 'Overhead Press',
  romanian_deadlift: 'RDL',
  pull_up: 'Pull-up',
};

const ALL_EXERCISES = Object.keys(EXERCISE_LABELS);

function formatVolume(kg) {
  if (kg >= 1000) {
    return `${(kg / 1000).toFixed(1)}t`;
  }
  return `${Math.round(kg)} kg`;
}

function groupVolumeByWeek(volumeData) {
  const weeks = {};
  volumeData.forEach(({ date, total_volume }) => {
    const d = new Date(date);
    const weekStart = new Date(d);
    weekStart.setDate(d.getDate() - d.getDay());
    const key = weekStart.toISOString().slice(0, 10);
    weeks[key] = (weeks[key] || 0) + total_volume;
  });
  return Object.entries(weeks)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-4)
    .map(([week, volume]) => ({
      week: week.slice(5),
      volume: Math.round(volume),
    }));
}

function formLineColor(score) {
  if (score >= 80) return '#00ff88';
  if (score >= 60) return '#ffd54f';
  return '#ff5252';
}

export default function Dashboard({ recentPrExercise }) {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [chartExercise, setChartExercise] = useState('squat');
  const [history, setHistory] = useState([]);
  const [volume, setVolume] = useState([]);
  const [formTrend, setFormTrend] = useState([]);

  const trainedExercises = useMemo(() => {
    if (!dashboard?.prs?.length) {
      return ALL_EXERCISES;
    }
    const fromPrs = dashboard.prs.map((p) => p.exercise);
    const fromRecent = (dashboard.recent_sessions || []).map((s) => s.exercise);
    const combined = [...new Set([...fromPrs, ...fromRecent])];
    return combined.length ? combined : ALL_EXERCISES;
  }, [dashboard]);

  useEffect(() => {
    if (trainedExercises.length && !trainedExercises.includes(chartExercise)) {
      setChartExercise(trainedExercises[0]);
    }
  }, [trainedExercises, chartExercise]);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDashboard();
      setDashboard(data);
      if (data.recent_sessions?.length) {
        setChartExercise(data.recent_sessions[0].exercise);
      }
    } catch (err) {
      setError(err.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!chartExercise) {
      return;
    }

    let cancelled = false;

    async function loadCharts() {
      try {
        const [hist, vol, form] = await Promise.all([
          fetchExerciseHistory(chartExercise),
          fetchExerciseVolume(chartExercise),
          fetchFormTrend(chartExercise),
        ]);
        if (!cancelled) {
          setHistory(
            [...(hist.sets || [])].reverse().map((s) => ({
              date: s.date?.slice(0, 10) || '',
              e1rm: s.e1rm,
              weight: s.weight_kg,
              reps: s.reps_completed,
            }))
          );
          setVolume(vol.volume || []);
          setFormTrend(form.trend || []);
        }
      } catch {
        if (!cancelled) {
          setHistory([]);
          setVolume([]);
          setFormTrend([]);
        }
      }
    }

    loadCharts();
    return () => {
      cancelled = true;
    };
  }, [chartExercise]);

  const weeklyVolume = useMemo(() => groupVolumeByWeek(volume), [volume]);

  if (loading) {
    return <div className="dashboard dashboard--loading">Loading dashboard…</div>;
  }

  if (error) {
    return (
      <div className="dashboard dashboard--error">
        <p>{error}</p>
        <button type="button" onClick={loadDashboard}>
          Retry
        </button>
      </div>
    );
  }

  const empty = !dashboard?.total_sessions;

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        <h2 className="dashboard__title">Your Training</h2>
        <div className="dashboard__summary-row">
          <div className="dashboard__stat">
            <span className="dashboard__stat-value">{dashboard?.total_sessions ?? 0}</span>
            <span className="dashboard__stat-label">Sessions</span>
          </div>
          <div className="dashboard__stat">
            <span className="dashboard__stat-value">
              {formatVolume(dashboard?.total_volume_kg ?? 0)}
            </span>
            <span className="dashboard__stat-label">Total volume</span>
          </div>
          <div className="dashboard__stat">
            <span className="dashboard__stat-value">{dashboard?.streak ?? 0}</span>
            <span className="dashboard__stat-label">Day streak</span>
          </div>
        </div>
      </header>

      {empty ? (
        <p className="dashboard__empty">No sessions yet — start training!</p>
      ) : (
        <>
          <section className="dashboard__section">
            <h3 className="dashboard__section-title">Personal Records</h3>
            {dashboard.prs?.length ? (
              <div className="pr-grid">
                {dashboard.prs.map((pr) => (
                  <div
                    key={pr.exercise}
                    className={`pr-card ${recentPrExercise === pr.exercise ? 'pr-card--new' : ''}`}
                  >
                    {recentPrExercise === pr.exercise && (
                      <span className="pr-card__badge">New</span>
                    )}
                    <span className="pr-card__name">
                      {EXERCISE_LABELS[pr.exercise] || pr.exercise}
                    </span>
                    <span className="pr-card__lift">
                      {pr.weight_kg}kg × {pr.reps}
                    </span>
                    <span className="pr-card__e1rm">e1RM {pr.e1rm}kg</span>
                    <span className="pr-card__date">
                      {pr.date ? new Date(pr.date).toLocaleDateString() : ''}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="dashboard__muted">No PRs logged yet.</p>
            )}
          </section>

          <section className="dashboard__section">
            <div className="dashboard__tabs">
              {trainedExercises.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  className={`dashboard__tab ${chartExercise === ex ? 'dashboard__tab--active' : ''}`}
                  onClick={() => setChartExercise(ex)}
                >
                  {EXERCISE_LABELS[ex] || ex}
                </button>
              ))}
            </div>

            <h3 className="dashboard__section-title">Estimated 1RM trend</h3>
            <div className="dashboard__chart">
              {history.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={history}>
                    <XAxis dataKey="date" stroke="#666" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#666" tick={{ fontSize: 11 }} unit=" kg" />
                    <Tooltip
                      contentStyle={{ background: '#141414', border: '1px solid #333' }}
                      labelStyle={{ color: '#aaa' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="e1rm"
                      stroke="#00ff88"
                      strokeWidth={2}
                      dot={{ fill: '#00ff88', r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="dashboard__muted">No history for this exercise yet.</p>
              )}
            </div>

            <h3 className="dashboard__section-title">Weekly volume (last 4 weeks)</h3>
            <div className="dashboard__chart">
              {weeklyVolume.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={weeklyVolume}>
                    <XAxis dataKey="week" stroke="#666" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#666" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ background: '#141414', border: '1px solid #333' }}
                    />
                    <Bar dataKey="volume" fill="#00ff88" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="dashboard__muted">No volume data yet.</p>
              )}
            </div>

            <h3 className="dashboard__section-title">Form score trend</h3>
            <div className="dashboard__chart">
              {formTrend.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={formTrend}>
                    <XAxis dataKey="session_date" stroke="#666" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} stroke="#666" tick={{ fontSize: 11 }} unit="%" />
                    <Tooltip
                      contentStyle={{ background: '#141414', border: '1px solid #333' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="avg_form_score"
                      stroke="#00ff88"
                      strokeWidth={2}
                      dot={(props) => {
                        const { cx, cy, payload } = props;
                        return (
                          <circle
                            cx={cx}
                            cy={cy}
                            r={4}
                            fill={formLineColor(payload.avg_form_score)}
                            stroke="#0a0a0a"
                          />
                        );
                      }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="dashboard__muted">No form scores logged yet.</p>
              )}
            </div>
          </section>

          <section className="dashboard__section">
            <h3 className="dashboard__section-title">Recent sessions</h3>
            {dashboard.recent_sessions?.length ? (
              <ul className="recent-sessions">
                {dashboard.recent_sessions.map((s) => (
                  <li key={s.session_id} className="recent-session">
                    <div className="recent-session__main">
                      <span className="recent-session__exercise">
                        {EXERCISE_LABELS[s.exercise] || s.exercise}
                      </span>
                      <span className="recent-session__date">
                        {new Date(s.date).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="recent-session__meta">
                      <span>
                        {s.sets_count} sets · {s.total_reps} reps
                      </span>
                      <span>
                        Top: {s.top_set_weight}kg × {s.top_set_reps}
                      </span>
                      <span
                        className={`recent-session__form ${
                          s.avg_form_score >= 80
                            ? 'recent-session__form--good'
                            : s.avg_form_score >= 60
                              ? 'recent-session__form--ok'
                              : 'recent-session__form--low'
                        }`}
                      >
                        Form {s.avg_form_score}%
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="dashboard__muted">No recent sessions.</p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
