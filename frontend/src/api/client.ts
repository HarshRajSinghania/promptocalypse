export const API_BASE = '/api';

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

export async function submitKey(userId: string, key: string) {
  // TODO: POST /api/submit-key
  void userId;
  void key;
  throw new Error('Not implemented');
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
