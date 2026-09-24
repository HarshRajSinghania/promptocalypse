import type { SubmitKeyResponse, User } from '../types'

export const API_BASE =
  (import.meta.env?.VITE_API_BASE as string | undefined) || '/api';

export async function registerUser(
  username: string,
  email?: string
): Promise<User> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email }),
  })
  if (!res.ok) {
    const errorData = (await res.json().catch(() => ({}))) as {
      detail?: string
    }
    throw new Error(errorData.detail || 'Sign-in failed')
  }
  return (await res.json()) as User
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

export async function fetchUserState(userId: string): Promise<User> {
  const res = await fetch(
    `${API_BASE}/user/state?user_id=${encodeURIComponent(userId)}`
  )
  if (!res.ok) {
    const errorData = (await res.json().catch(() => ({}))) as {
      detail?: string
    }
    throw new Error(errorData.detail || 'Failed to fetch user state')
  }
  return (await res.json()) as User
}
