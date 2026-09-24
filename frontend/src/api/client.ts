import type { SubmitKeyResponse } from '../types'

export const API_BASE =
  (import.meta.env?.VITE_API_BASE as string | undefined) || '/api';

export async function registerUser(username: string) {
  // TODO: POST /api/auth/register
  void username;
  throw new Error('Not implemented');
}

export async function sendPrompt(userId: string, prompt: string) {
  // TODO: POST /api/chat
  void userId;
  void prompt;
  throw new Error('Not implemented');
}

export async function submitKey(
  userId: string,
  key: string
): Promise<SubmitKeyResponse> {
  const res = await fetch(`${API_BASE}/submit-key`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, key }),
  })
  if (!res.ok) {
    const errorData = (await res.json().catch(() => ({}))) as {
      detail?: string
    }
    throw new Error(errorData.detail || 'Key submission failed')
  }
  return (await res.json()) as SubmitKeyResponse
}

export async function fetchLeaderboard() {
  // TODO: GET /api/leaderboard
  throw new Error('Not implemented');
}

export async function fetchUserState(userId: string) {
  // TODO: GET /api/user/state
  void userId;
  throw new Error('Not implemented');
}
