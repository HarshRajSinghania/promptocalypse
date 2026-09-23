export interface User {
  user_id: string;
  username: string;
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
  current_level: number;
  active_cooldown_until: number | null;
  local_chat_history: Record<string, ChatMessage[]>;
}
