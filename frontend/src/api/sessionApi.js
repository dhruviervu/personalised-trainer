/**
 * REST API client for AI coach sessions.
 */

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail || data.error || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function startSession(exercise, goal, weightKg) {
  const response = await fetch('/api/session/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      exercise,
      goal: goal.toLowerCase(),
      weight_kg: Number(weightKg),
    }),
  });
  return parseResponse(response);
}

export async function completeSet(sessionId, setData, weightKg) {
  const response = await fetch(`/api/session/${sessionId}/set-complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ set_data: setData, weight_kg: Number(weightKg) }),
  });
  return parseResponse(response);
}

export async function chatWithCoach(sessionId, message) {
  const response = await fetch(`/api/session/${sessionId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  return parseResponse(response);
}

export async function endSession(sessionId) {
  const response = await fetch(`/api/session/${sessionId}/end`, {
    method: 'POST',
  });
  return parseResponse(response);
}

export async function getAllSessions() {
  const response = await fetch('/api/sessions');
  return parseResponse(response);
}

export async function getLastSession(exercise) {
  const response = await fetch(`/api/sessions/last/${exercise}`);
  return parseResponse(response);
}
