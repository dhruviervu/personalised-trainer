import { useCallback, useEffect, useMemo, useState } from 'react';
import { endSession } from './api/sessionApi';
import Camera from './components/Camera';
import CoachChat from './components/CoachChat';
import ExerciseSelector from './components/ExerciseSelector';
import FormFeedback from './components/FormFeedback';
import RepCounter from './components/RepCounter';
import SessionBriefing from './components/SessionBriefing';
import SessionSetup from './components/SessionSetup';
import SessionSummary from './components/SessionSummary';
import { useWebSocket } from './hooks/useWebSocket';
import Dashboard from './pages/Dashboard';
import { WS_URL } from './config.js';

const WS_PATH = '/ws/session';

const EXERCISE_LABELS = {
  squat: 'Squat',
  deadlift: 'Deadlift',
  bench_press: 'Bench Press',
  overhead_press: 'Overhead Press',
  romanian_deadlift: 'Romanian Deadlift',
  pull_up: 'Pull-up',
};

function resetTrackingState(setters) {
  setters.setRepCount(0);
  setters.setGoodReps(0);
  setters.setBadReps(0);
  setters.setPhase('standing');
  setters.setFeedback('Connect and step into frame to begin.');
  setters.setFormFlags([]);
  setters.setLandmarks([]);
  setters.setCameraAngle('front');
  setters.setCurrentSetStartReps(0);
  setters.setCurrentSetStartGood(0);
  setters.setCurrentSetStartBad(0);
  setters.setCurrentSetFormFlags([]);
}

export default function App() {
  const [activeView, setActiveView] = useState('train');
  const [selectedExercise, setSelectedExercise] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [goal, setGoal] = useState('');
  const [weightKg, setWeightKg] = useState(0);
  const [openingMessage, setOpeningMessage] = useState('');
  const [setNumber, setSetNumber] = useState(0);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [pendingSetData, setPendingSetData] = useState(null);
  const [sessionSummary, setSessionSummary] = useState(null);
  const [completedSets, setCompletedSets] = useState([]);
  const [endingSession, setEndingSession] = useState(false);
  const [recentPrExercise, setRecentPrExercise] = useState(null);
  const [isChangingExercise, setIsChangingExercise] = useState(false);
  const [isBriefingReady, setIsBriefingReady] = useState(false);

  const [currentSetStartReps, setCurrentSetStartReps] = useState(0);
  const [currentSetStartGood, setCurrentSetStartGood] = useState(0);
  const [currentSetStartBad, setCurrentSetStartBad] = useState(0);
  const [currentSetFormFlags, setCurrentSetFormFlags] = useState([]);

  const sessionActive = Boolean(sessionId && selectedExercise);
  const sessionInProgress = Boolean(sessionId);
  const showNavTabs = !sessionInProgress;

  const wsUrl = useMemo(() => {
    if (!sessionActive) {
      return null;
    }
    return `${WS_URL}${WS_PATH}`;
  }, [sessionActive]);

  const {
    sendFrame,
    sendConfig,
    sendResetSet,
    lastMessage,
    connectionStatus,
    configReady,
    disconnect,
    resetForNewSession,
  } = useWebSocket(wsUrl, { enabled: sessionActive, autoReconnect: true });

  const [repCount, setRepCount] = useState(0);
  const [setReps, setSetReps] = useState(0);
  const [goodReps, setGoodReps] = useState(0);
  const [badReps, setBadReps] = useState(0);
  const [phase, setPhase] = useState('standing');
  const [feedback, setFeedback] = useState('Connect and step into frame to begin.');
  const [formFlags, setFormFlags] = useState([]);
  const [landmarks, setLandmarks] = useState([]);
  const [cameraAngle, setCameraAngle] = useState('front');
  const [wsError, setWsError] = useState(null);

  const handleSelectExercise = useCallback((exerciseId) => {
    setWsError(null);
    setSessionSummary(null);
    if (!isChangingExercise) {
      setCompletedSets([]);
      setSetNumber(0);
      setSessionId(null);
    }
    setActiveView('train');
    setIsBriefingReady(false);
    resetTrackingState({
      setRepCount,
      setGoodReps,
      setBadReps,
      setPhase,
      setFeedback,
      setFormFlags,
      setLandmarks,
      setCameraAngle,
      setCurrentSetStartReps,
      setCurrentSetStartGood,
      setCurrentSetStartBad,
      setCurrentSetFormFlags,
    });
    setSelectedExercise(exerciseId);
  }, [isChangingExercise]);

  const handleSessionReady = useCallback(
    ({ sessionId: id, goal: g, weightKg: w, openingMessage: msg }) => {
      setSessionId(id);
      setGoal(g);
      setWeightKg(w);
      setOpeningMessage(msg);
      if (!isChangingExercise) {
        setSetNumber(0);
        setCompletedSets([]);
      }
      resetTrackingState({
        setRepCount,
        setGoodReps,
        setBadReps,
        setPhase,
        setFeedback,
        setFormFlags,
        setLandmarks,
        setCameraAngle,
        setCurrentSetStartReps,
        setCurrentSetStartGood,
        setCurrentSetStartBad,
        setCurrentSetFormFlags,
      });
      if (isChangingExercise) {
        setIsChangingExercise(false);
        setIsBriefingReady(true);
      } else {
        setIsBriefingReady(false);
      }
    },
    [isChangingExercise]
  );

  const handleBackToExercises = useCallback(() => {
    disconnect();
    resetForNewSession();
    setSelectedExercise(null);
    setSessionId(null);
    setWsError(null);
    setSessionSummary(null);
  }, [disconnect, resetForNewSession]);

  const handleNewSession = useCallback(() => {
    disconnect();
    resetForNewSession();
    setSelectedExercise(null);
    setSessionId(null);
    setSessionSummary(null);
    setCompletedSets([]);
    setSetNumber(0);
    setIsChatOpen(false);
    setPendingSetData(null);
    setWsError(null);
    setActiveView('train');
    setIsChangingExercise(false);
    setIsBriefingReady(false);
  }, [disconnect, resetForNewSession]);

  const handleViewDashboard = useCallback(() => {
    setSessionSummary(null);
    setSelectedExercise(null);
    setSessionId(null);
    setActiveView('dashboard');
    setIsChangingExercise(false);
    setIsBriefingReady(false);
  }, []);

  const recordCompletedSet = useCallback(() => {
    if (!pendingSetData) {
      return;
    }
    setCompletedSets((prev) => [
      ...prev,
      {
        exercise: selectedExercise,
        reps: pendingSetData.reps_completed,
        good: pendingSetData.good_reps,
        bad: pendingSetData.bad_reps,
        setNumber,
      },
    ]);
    setPendingSetData(null);
  }, [pendingSetData, selectedExercise, setNumber]);

  const handleSwitchExercise = useCallback(() => {
    recordCompletedSet();
    setIsChatOpen(false);
    disconnect();
    resetForNewSession();
    setSelectedExercise(null);
    setIsChangingExercise(true);
    setIsBriefingReady(false);
    setWsError(null);
  }, [recordCompletedSet, disconnect, resetForNewSession]);

  const handleStartFromBriefing = useCallback(() => {
    setIsBriefingReady(true);
  }, []);

  const handleEndSession = useCallback(async () => {
    if (!sessionId || endingSession) {
      return;
    }

    setEndingSession(true);
    disconnect();

    try {
      const result = await endSession(sessionId);

      const totalReps = completedSets.reduce((sum, s) => sum + s.reps, 0);
      const totalGood = completedSets.reduce((sum, s) => sum + s.good, 0);
      const goodRepPercent =
        totalReps > 0 ? Math.round((totalGood / totalReps) * 100) : 0;

      if (result.is_pr && selectedExercise) {
        setRecentPrExercise(selectedExercise);
      }

      const apiExercises = result.exercises ?? [];
      const apiTotalSets = result.total_sets ?? completedSets.length;
      const apiTotalReps = result.total_reps ?? totalReps;

      setSessionSummary({
        exercise: apiExercises.length === 1 ? apiExercises[0].exercise : null,
        exercises: apiExercises,
        goal,
        weightKg,
        totalSets: apiTotalSets,
        totalReps: apiTotalReps,
        goodRepPercent: result.form_score_percent ?? goodRepPercent,
        formScorePercent: result.form_score_percent ?? goodRepPercent,
        topSet: result.top_set,
        sessionE1rm: result.session_e1rm ?? 0,
        isPr: result.is_pr ?? false,
        progressionAdvice: result.progression_advice,
        progression: result.progression,
        totalVolumeKg: result.total_volume_kg ?? 0,
      });
    } catch (err) {
      setSessionSummary({
        exercise: selectedExercise,
        exercises: [],
        goal,
        weightKg,
        totalSets: completedSets.length,
        totalReps: completedSets.reduce((sum, s) => sum + s.reps, 0),
        goodRepPercent: 0,
        progressionAdvice: err.message || 'Could not load progression advice.',
      });
    } finally {
      setEndingSession(false);
      setIsChatOpen(false);
    }
  }, [
    sessionId,
    endingSession,
    disconnect,
    completedSets,
    selectedExercise,
    goal,
    weightKg,
  ]);

  const handleSetComplete = useCallback(() => {
    const setData = {
      reps_completed: Math.max(0, repCount - currentSetStartReps),
      good_reps: Math.max(0, goodReps - currentSetStartGood),
      bad_reps: Math.max(0, badReps - currentSetStartBad),
      form_flags: [...currentSetFormFlags],
      set_reps: setReps,
      end_rep_count: repCount,
      end_good_reps: goodReps,
      end_bad_reps: badReps,
    };

    const completedSetNumber = setNumber + 1;
    setSetNumber(completedSetNumber);
    setPendingSetData(setData);
    setIsChatOpen(true);
  }, [
    repCount,
    goodReps,
    badReps,
    currentSetStartReps,
    currentSetStartGood,
    currentSetStartBad,
    currentSetFormFlags,
    setNumber,
  ]);

  const handleNextSet = useCallback(() => {
    recordCompletedSet();

    setCurrentSetStartReps(repCount);
    setCurrentSetStartGood(goodReps);
    setCurrentSetStartBad(badReps);
    setCurrentSetFormFlags([]);
    setIsChatOpen(false);
  }, [recordCompletedSet, repCount, goodReps, badReps]);

  const handlePrAchieved = useCallback(() => {
    if (selectedExercise) {
      setRecentPrExercise(selectedExercise);
    }
  }, [selectedExercise]);

  useEffect(() => {
    if (connectionStatus === 'connected' && selectedExercise && sessionId && !configReady) {
      sendConfig({ exercise: selectedExercise, session_id: sessionId });
    }
  }, [connectionStatus, selectedExercise, sessionId, configReady, sendConfig]);

  useEffect(() => {
    if (!lastMessage) {
      return;
    }

    if (lastMessage.error) {
      setWsError(lastMessage.error);
      disconnect();
      return;
    }

    if (lastMessage.action === 'set_reset') {
      setCurrentSetStartReps(lastMessage.total_reps ?? repCount);
      setSetReps(0);
      return;
    }

    setRepCount(lastMessage.rep_count ?? 0);
    setSetReps(
      lastMessage.set_reps ??
        Math.max(0, (lastMessage.rep_count ?? 0) - currentSetStartReps)
    );
    setGoodReps(lastMessage.good_reps ?? 0);
    setBadReps(lastMessage.bad_reps ?? 0);
    setPhase(lastMessage.phase ?? 'standing');
    setFeedback(lastMessage.feedback ?? '');
    setFormFlags(lastMessage.form_flags ?? []);
    setLandmarks(lastMessage.landmarks ?? []);

    if (lastMessage.camera_angle) {
      setCameraAngle(lastMessage.camera_angle);
    }

    if (lastMessage.form_flags?.length) {
      setCurrentSetFormFlags((prev) => {
        const next = new Set(prev);
        lastMessage.form_flags.forEach((flag) => {
          if (flag !== 'good_rep') {
            next.add(flag);
          }
        });
        return [...next];
      });
    }
  }, [lastMessage, disconnect, currentSetStartReps, repCount]);

  const statusClass =
    connectionStatus === 'connected'
      ? 'status-indicator--connected'
      : 'status-indicator--disconnected';

  const exerciseLabel = EXERCISE_LABELS[selectedExercise] || selectedExercise;

  return (
    <div className="app">
      <header
        className={`app-header${sessionInProgress && activeView === 'train' ? ' app-header--session' : ''}`}
      >
        {sessionInProgress && activeView === 'train' && !sessionSummary && (
          <div className="session-toolbar">
            <div className="session-toolbar__left">
              {sessionActive && (
                <button
                  type="button"
                  className="change-exercise-btn"
                  onClick={handleSwitchExercise}
                >
                  ↔ Change Exercise
                </button>
              )}
            </div>
            <div className="session-toolbar__right">
              <div className={`status-indicator ${statusClass}`} title={connectionStatus}>
                <span className="status-dot" />
                <span className="status-text">{connectionStatus}</span>
              </div>
              <button
                type="button"
                className="end-session-btn"
                onClick={handleEndSession}
                disabled={endingSession}
              >
                ⏹ End Session
              </button>
            </div>
          </div>
        )}
        {!(sessionInProgress && activeView === 'train' && !sessionSummary) && (
          <div className={`status-indicator ${statusClass}`} title={connectionStatus}>
            <span className="status-dot" />
            <span className="status-text">{connectionStatus}</span>
          </div>
        )}
        <h1 className="app-title">AI Personal Trainer</h1>
        <p className="app-subtitle">
          {sessionActive
            ? `${exerciseLabel} · ${goal} · ${weightKg}kg`
            : 'Phase 4 · Progress & PRs'}
        </p>

        {showNavTabs && (
          <nav className="app-tabs" aria-label="Main navigation">
            <button
              type="button"
              className={`app-tab ${activeView === 'train' ? 'app-tab--active' : ''}`}
              onClick={() => setActiveView('train')}
            >
              🏋️ Train
            </button>
            <button
              type="button"
              className={`app-tab ${activeView === 'dashboard' ? 'app-tab--active' : ''}`}
              onClick={() => setActiveView('dashboard')}
            >
              📊 Dashboard
            </button>
          </nav>
        )}
      </header>

      <main className="app-main">
        {activeView === 'dashboard' && (
          <Dashboard recentPrExercise={recentPrExercise} />
        )}

        {activeView === 'train' && !selectedExercise && (
          <ExerciseSelector onSelect={handleSelectExercise} />
        )}

        {activeView === 'train' && selectedExercise && (!sessionId || isChangingExercise) && (
          <SessionSetup
            exercise={selectedExercise}
            exerciseLabel={exerciseLabel}
            onSessionReady={handleSessionReady}
            onBack={() => {
              if (sessionId && isChangingExercise) {
                setIsChangingExercise(false);
                setIsBriefingReady(true);
              } else {
                setSelectedExercise(null);
              }
            }}
            isNewSession={!sessionId}
            existingGoal={goal}
            existingWeightKg={weightKg}
            existingSessionId={sessionId}
            existingOpeningMessage={openingMessage}
          />
        )}

        {activeView === 'train' && sessionActive && !isBriefingReady && !isChangingExercise && (
          <SessionBriefing
            exercise={exerciseLabel}
            goal={goal}
            weightKg={weightKg}
            sessionId={sessionId}
            openingMessage={openingMessage}
            onStartSession={handleStartFromBriefing}
          />
        )}

        {activeView === 'train' && sessionActive && isBriefingReady && (
          <>
            {wsError && (
              <div className="ws-error" role="alert">
                {wsError}
              </div>
            )}

            <RepCounter
              setReps={setReps}
              totalReps={repCount}
            />

            <section className="video-section">
              <div className="camera-angle-banner">
                📷 {cameraAngle} view recommended
              </div>
              <Camera
                sendFrame={sendFrame}
                landmarks={landmarks}
                connectionStatus={connectionStatus}
                configReady={configReady}
              />
              <FormFeedback feedback={feedback} formFlags={formFlags} phase={phase} />

              {!isChatOpen && (
                <button
                  type="button"
                  className="set-complete-btn"
                  onClick={handleSetComplete}
                >
                  Set Complete
                </button>
              )}
            </section>

            <CoachChat
              sessionId={sessionId}
              weightKg={weightKg}
              setNumber={setNumber}
              setData={pendingSetData}
              openingMessage={openingMessage}
              isOpen={isChatOpen}
              onNextSet={handleNextSet}
              onChangeExercise={handleSwitchExercise}
              onPrAchieved={handlePrAchieved}
              sendResetSet={sendResetSet}
            />
          </>
        )}
      </main>

      <SessionSummary
        summary={sessionSummary}
        onNewSession={handleNewSession}
        onViewDashboard={handleViewDashboard}
      />
    </div>
  );
}
