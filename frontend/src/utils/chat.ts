import type { ChatMessage } from '../types/index.ts'
import { loadSession, saveSession } from './session.ts'

export interface CreateMessageOptions {
  sender: 'user' | 'assistant' | 'system_alert' | 'bot' | 'system'
  content: string
  latency_ms?: number
  status?: 'success' | 'blocked' | 'error'
  isBlocked?: boolean
  level?: number
  id?: string
  timestamp?: number | string
}

/**
 * Generates a unique message identifier.
 */
export function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

/**
 * Inspects a message reply and status for firewall or token scrubber intercepts.
 */
export function detectFirewallIntercept(
  reply: string,
  status?: string
): {
  isBlocked: boolean
  isLeak: boolean
} {
  const isBlocked =
    status === 'blocked' ||
    reply.includes('Firewall Alert:') ||
    reply.includes('[FIREWALL INTERCEPT')

  const isLeak = reply.includes('[Leak Detected:')

  return { isBlocked, isLeak }
}

/**
 * Creates a compliant ChatMessage with normalized fields.
 */
export function createChatMessage(opts: CreateMessageOptions): ChatMessage {
  const content = opts.content || ''
  const intercept = detectFirewallIntercept(content, opts.status)
  const isBlocked = opts.isBlocked ?? intercept.isBlocked
  const status =
    opts.status ??
    (isBlocked
      ? 'blocked'
      : opts.sender === 'system_alert'
        ? 'error'
        : 'success')

  return {
    id: opts.id || generateMessageId(),
    sender: opts.sender,
    content,
    text: content,
    timestamp: opts.timestamp || Date.now(),
    latency_ms: opts.latency_ms,
    status,
    isBlocked,
    level: opts.level,
  }
}

/**
 * Formats API errors (400, 404, 429, 502, etc.) into readable terminal alert text.
 */
export function formatErrorAlert(err: unknown): string {
  if (!err) return '[ Connection error — retry after cooldown ]'
  if (typeof err === 'object') {
    const errorObj = err as { status?: number; detail?: string; message?: string }
    if (
      errorObj.status === 429 ||
      errorObj.message?.includes('429') ||
      errorObj.detail?.toLowerCase().includes('cooldown') ||
      errorObj.detail?.toLowerCase().includes('rate limit')
    ) {
      return (
        errorObj.detail ||
        '[ 429 Too Many Requests — Rate limit in effect, please wait ]'
      )
    }
    if (errorObj.status === 502 || errorObj.message?.includes('502')) {
      return errorObj.detail || '[ 502 Bad Gateway — Upstream LLM unreachable ]'
    }
    if (errorObj.status === 404 || errorObj.message?.includes('404')) {
      return errorObj.detail || '[ 404 Not Found — Active user session not found ]'
    }
    if (errorObj.detail) {
      return `[ Alert: ${errorObj.detail} ]`
    }
    if (errorObj.message) {
      return `[ Alert: ${errorObj.message} ]`
    }
  }
  return String(err)
}

/**
 * Returns the persona tag for a given message sender and level.
 */
export function getPersonaLabel(
  sender: 'user' | 'assistant' | 'system_alert' | 'bot' | 'system',
  level: number = 1,
  isBlocked: boolean = false,
  isLeak: boolean = false
): string {
  if (sender === 'user') {
    return '> YOU'
  }
  if (sender === 'system_alert' || sender === 'system') {
    return '⚠ SYSTEM ALERT'
  }
  if (isBlocked) {
    return `TARGET_BOT [L${level}] [BLOCKED]`
  }
  if (isLeak) {
    return `TARGET_BOT [L${level}] [LEAK MASKED]`
  }
  return `TARGET_BOT [L${level}]`
}

/**
 * Loads conversation state per level from local session.
 */
export function getStoredChatHistory(): Record<number, ChatMessage[]> {
  const session = loadSession()
  if (session?.local_chat_history) {
    const result: Record<number, ChatMessage[]> = {}
    for (const [k, msgs] of Object.entries(session.local_chat_history)) {
      const lvl = parseInt(k, 10)
      if (!isNaN(lvl) && Array.isArray(msgs)) {
        result[lvl] = msgs
      }
    }
    return result
  }
  return {}
}

/**
 * Persists conversation state per level into local session.
 */
export function saveChatHistory(history: Record<number, ChatMessage[]>): void {
  const session = loadSession()
  if (session) {
    session.local_chat_history = {
      ...(session.local_chat_history || {}),
      ...Object.fromEntries(
        Object.entries(history).map(([k, v]) => [String(k), v])
      ),
    }
    saveSession(session)
  }
}
