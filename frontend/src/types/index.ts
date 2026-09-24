export interface User {
  user_id: string;
  username: string;
  email?: string;
  current_level: number;
  start_time: string;
  total_prompts: number;
  failed_attempts: number;
  completed: boolean;
}

export interface ChatMessage {
  sender: 'user' | 'bot' | 'system';
  text: string;
  timestamp: number;
  isBlocked?: boolean;
}

export interface LeaderboardEntry {
  rank: number;
  username: string;
  current_level: number;
  score: number;
  prompts: number;
  chars: number;
  completed: boolean;
}

export interface SessionState {
  user_id: string;
  username: string;
  email?: string;
  current_level: number;
  active_cooldown_until?: number | null;
  local_chat_history?: Record<string, ChatMessage[]>;
  start_time?: string;
  total_prompts?: number;
  total_chars?: number;
  failed_attempts?: number;
  completed?: boolean;
  final_score?: number;
  cached_at?: number;
}

export interface SubmitKeyResponse {
  status: 'correct' | 'incorrect' | 'completed' | string;
  unlocked_level?: number;
  message: string;
  penalty_points?: number;
  final_score?: number;
  completion_time?: string;
  stats?: {
    total_prompts: number;
    elapsed_minutes: number;
    failed_attempts: number;
  };
}

