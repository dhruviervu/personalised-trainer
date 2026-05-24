import { useState } from 'react';
import { chatWithCoach } from '../api/sessionApi';

const BRIEFINGS = {
  strength:
    'Focus on 3-5 heavy reps per set. Each rep should be controlled and intentional. Rest 3-5 minutes between sets — full recovery matters more than speed. Leave 1-2 reps in the tank on your first sets, push closer to the limit on your last.',
  hypertrophy:
    'Aim for 6-12 reps per set, taken close to failure — the last 2-3 reps should be genuinely hard. Rest 90 seconds to 2 minutes between sets. Focus on feeling the muscle work, not just moving the weight.',
  endurance:
    'Higher rep ranges today — 15+ reps, moderate weight. Keep rest short (45-60 seconds). The burn is the point. Maintain form even when it gets uncomfortable.',
  cut:
    'Training on a cut is the same as training normally — your job is to maintain the strength and muscle you have built. Do not switch to high reps and light weight. Train with the same intensity as usual. Recovery may feel slightly harder — that is normal. If a weight feels unusually heavy today, it is okay to keep it the same rather than pushing for a PR.',
};

export default function SessionBriefing({
  exercise,
  goal,
  weightKg,
  sessionId,
  openingMessage,
  onStartSession,
}) {
  const [messages, setMessages] = useState(
    openingMessage ? [{ role: 'coach', content: openingMessage }] : []
  );
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const goalKey = (goal || 'strength').toLowerCase();

  const sendMessage = async (event) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || !sessionId || loading) {
      return;
    }

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');
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

  return (
    <div style={{ width: '100%', maxWidth: 720 }}>
      <h2 style={{ marginBottom: 8 }}>Your {exercise} session</h2>
      <p style={{ color: '#999', marginBottom: 12 }}>
        Goal: {goal} · Working load: {weightKg}kg
      </p>
      <div
        style={{
          background: '#1a1a1a',
          border: '1px solid #2a2a2a',
          borderRadius: 12,
          padding: 16,
          lineHeight: 1.5,
          marginBottom: 14,
        }}
      >
        {BRIEFINGS[goalKey] || BRIEFINGS.strength}
      </div>

      <div
        style={{
          background: '#141414',
          border: '1px solid #2a2a2a',
          borderRadius: 12,
          padding: 12,
          marginBottom: 12,
        }}
      >
        <div style={{ maxHeight: 220, overflowY: 'auto', paddingBottom: 8 }}>
          {messages.map((msg, idx) => (
            <div
              key={`${msg.role}-${idx}`}
              style={{
                maxWidth: '85%',
                marginBottom: 8,
                marginLeft: msg.role === 'coach' ? 0 : 'auto',
                background: msg.role === 'coach' ? '#222' : 'rgba(0,255,136,0.15)',
                border:
                  msg.role === 'coach' ? '1px solid #333' : '1px solid rgba(0,255,136,0.35)',
                color: msg.role === 'coach' ? '#e0e0e0' : '#00ff88',
                borderRadius: 10,
                padding: '8px 10px',
              }}
            >
              {msg.content}
            </div>
          ))}
        </div>
        <form onSubmit={sendMessage} style={{ display: 'flex', gap: 8 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask before you start…"
            style={{
              flex: 1,
              background: '#0a0a0a',
              border: '1px solid #333',
              borderRadius: 8,
              color: '#fff',
              padding: '10px 12px',
            }}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            style={{
              padding: '10px 14px',
              background: '#00ff88',
              border: 'none',
              borderRadius: 8,
              color: '#0a0a0a',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Send
          </button>
        </form>
      </div>

      <button
        type="button"
        onClick={onStartSession}
        style={{
          width: '100%',
          padding: '12px 14px',
          background: '#00ff88',
          border: 'none',
          borderRadius: 10,
          color: '#0a0a0a',
          fontWeight: 700,
          fontSize: 16,
          cursor: 'pointer',
        }}
      >
        Start Session
      </button>
    </div>
  );
}
