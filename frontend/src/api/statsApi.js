/**
 * Stats and dashboard API client.
 */

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail || data.error || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function fetchDashboard() {
  const response = await fetch('/api/dashboard');
  return parseResponse(response);
}

export async function fetchPRs() {
  const response = await fetch('/api/stats/prs');
  return parseResponse(response);
}

export async function fetchExerciseHistory(exercise) {
  const response = await fetch(`/api/stats/history/${exercise}`);
  return parseResponse(response);
}

export async function fetchExerciseVolume(exercise) {
  const response = await fetch(`/api/stats/volume/${exercise}`);
  return parseResponse(response);
}

export async function fetchFormTrend(exercise) {
  const response = await fetch(`/api/stats/form/${exercise}`);
  return parseResponse(response);
}

export async function fetchBodyweight() {
  const response = await fetch('/api/stats/bodyweight');
  return parseResponse(response);
}

export async function logBodyweight(weightKg) {
  const response = await fetch('/api/stats/bodyweight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ weight_kg: Number(weightKg) }),
  });
  return parseResponse(response);
}
