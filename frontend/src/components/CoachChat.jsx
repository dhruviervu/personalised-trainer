import { useEffect, useRef, useState } from 'react';
import { chatWithCoach, completeSet } from '../api/sessionApi';

/**
 * Slide-up coach chat panel after each completed set.
 */
export default function CoachChat({
  sessionId,
  weightKg,
  setNumber,
  setData,
  openingMessage,
  isOpen,
  onNextSet,
  onChangeExercise,
  onPrAchieved,
  sendResetSet,
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const [prInfo, setPrInfo] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    setInitialized(false);
  }, [setNumber]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // First open after a set: request coach post-set message
  useEffect(() => {
    if (!isOpen || !sessionId || !setData || initialized) {
      return;
    }

    let cancelled = false;

    async function loadSetFeedback() {
      setLoading(true);
      try {
        const result = await completeSet(sessionId, setData, weightKg);
        if (!cancelled) {
          if (result.is_pr) {
            setPrInfo({ e1rm: result.e1rm });
            onPrAchieved?.(result.e1rm);
          }
          setMessages((prev) => [
            ...prev,
            { role: 'coach', content: result.coach_message },
          ]);
          setInitialized(true);
        }
      } catch (err) {
        if (!cancelled) {
          setMessages((prev) => [
            ...prev,
            {
              role: 'coach',
              content: 'Coach unavailable — log your RPE manually.',
            },
          ]);
          setInitialized(true);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadSetFeedback();

    return () => {
      cancelled = true;
    };
  }, [isOpen, sessionId, setData, weightKg, initialized]);

  const handleSend = async (event) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || loading) {
      return;
    }

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const result = await chatWithCoach(sessionId, text);
      setMessages((prev) => [...prev, { role: 'coach', content: result.coach_message }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'coach', content: 'Coach unavailable — log your RPE manually.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleNextSet = () => {
    if (sendResetSet) {
      sendResetSet();
    }
    setInitialized(false);
    setMessages([]);
    setPrInfo(null);
    onNextSet();
  };

  const handleChangeExercise = () => {
    setInitialized(false);
    setMessages([]);
    setPrInfo(null);
    onChangeExercise?.();
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="coach-chat-backdrop">
      <div className="coach-chat">
        <div className="coach-chat__header">
          <h3 className="coach-chat__title">Coach · Set {setNumber}</h3>
          <div className="coach-chat__actions">
            <button
              type="button"
              className="coach-chat__change-exercise"
              onClick={handleChangeExercise}
            >
              Change Exercise
            </button>
            <button type="button" className="coach-chat__next" onClick={handleNextSet}>
              Next Set →
            </button>
          </div>
        </div>

        {prInfo && (
          <div className="pr-banner" role="status">
            🏆 New PR! Estimated 1RM: {prInfo.e1rm}kg
          </div>
        )}

        <div className="coach-chat__messages" ref={scrollRef}>
          {messages.length === 0 && openingMessage && (
            <div className="chat-bubble chat-bubble--coach">{openingMessage}</div>
          )}
          {messages.map((msg, index) => (
            <div
              key={`${msg.role}-${index}`}
              className={`chat-bubble chat-bubble--${msg.role}`}
            >
              {msg.content}
            </div>
          ))}
          {loading && <div className="chat-bubble chat-bubble--coach chat-bubble--typing">…</div>}
        </div>

        <form className="coach-chat__input-row" onSubmit={handleSend}>
          <input
            type="text"
            className="coach-chat__input"
            placeholder="RPE (1–10), questions…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="coach-chat__send" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
