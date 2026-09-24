import { useState, useRef, useEffect, useCallback } from 'react'
import type { ChatMessage } from '../types'
import {
  COOLDOWN_MS,
  NOTICE_DISMISS_MS,
  feedbackForFailure,
  formatRttLabel,
  type ChatFailureKind,
} from '../utils/chatFeedback'
import { sendPrompt } from '../api/client'
import { loadSession, saveSession } from '../utils/session'
import {
  createChatMessage,
  detectFirewallIntercept,
  formatErrorAlert,
  getPersonaLabel,
  getStoredChatHistory,
  saveChatHistory,
} from '../utils/chat'
import './ChatTerminal.css'

const MAX_CHARS = 1000
const WARN_CHARS = 900

export interface ChatTerminalProps {
  userId?: string
  currentLevel?: number
  /**
   * Callback to send a prompt to the backend.
   * Returns the bot reply text, optional status ('blocked' for firewall
   * intercepts), the backend latency_ms / cooldown_seconds reported by the
   * API and the measured round-trip time from X-Process-Time (Issue #27).
   */
  onSendPrompt?: (prompt: string) => Promise<{
    reply: string
    status?: string
    latency_ms?: number
    cooldown_seconds?: number
    /** Measured X-Process-Time round trip; null when the header is absent. */
    latencyMs?: number | null
  }>
}

interface ChatNotice {
  kind: ChatFailureKind
  text: string
}

export default function ChatTerminal({
  userId = '',
  currentLevel = 1,
  onSendPrompt,
}: ChatTerminalProps) {
  const [messagesByLevel, setMessagesByLevel] = useState<
    Record<number, ChatMessage[]>
  >(() => getStoredChatHistory())
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isCoolingDown, setIsCoolingDown] = useState(false)
  const [notice, setNotice] = useState<ChatNotice | null>(null)
  const [rttMs, setRttMs] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const cooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const currentMessages = messagesByLevel[currentLevel] || []

  // Auto-scroll to bottom when messages, loading state, or current level changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [currentMessages, isLoading, currentLevel])

  // Auto-dismiss the toast banner after it has been visible for a while
  useEffect(() => {
    if (!notice) return
    const timer = setTimeout(() => setNotice(null), NOTICE_DISMISS_MS)
    return () => clearTimeout(timer)
  }, [notice])

  const clearCooldown = useCallback(() => {
    if (cooldownTimerRef.current !== null) {
      clearTimeout(cooldownTimerRef.current)
      cooldownTimerRef.current = null
    }
  }, [])

  // Starts (or restarts) the existing 3-second submission cooldown.
  const startCooldown = useCallback(() => {
    clearCooldown()
    setIsCoolingDown(true)
    cooldownTimerRef.current = setTimeout(() => {
      cooldownTimerRef.current = null
      setIsCoolingDown(false)
    }, COOLDOWN_MS)
  }, [clearCooldown])

  // Clear any pending cooldown timer on unmount
  useEffect(() => clearCooldown, [clearCooldown])

  const handleSubmit = useCallback(async () => {
    const trimmed = input.trim()
    if (!trimmed || isCoolingDown || isLoading) return

    // 1. Optimistically append user message
    const userMsg = createChatMessage({
      sender: 'user',
      content: trimmed,
      level: currentLevel,
    })

    setMessagesByLevel((prev) => {
      const prevList = prev[currentLevel] || []
      const nextList = [...prevList, userMsg]
      const nextMap = { ...prev, [currentLevel]: nextList }
      saveChatHistory(nextMap)
      return nextMap
    })
    setInput('')

    // 2. Start the 3-second submission cooldown (Issue #27 tracks the timer so
    //    a gateway failure can re-enable submission before it expires).
    startCooldown()

    // 3. Set typing / loading indicator
    setIsLoading(true)

    // Update prompt counter in session if session exists
    const session = loadSession()
    if (session) {
      session.total_prompts = (session.total_prompts || 0) + 1
      session.total_chars = (session.total_chars || 0) + trimmed.length
      saveSession(session)
    }

    try {
      let response: {
        reply: string
        status?: string
        latency_ms?: number
        cooldown_seconds?: number
        latencyMs?: number | null
      }

      if (onSendPrompt) {
        response = await onSendPrompt(trimmed)
      } else if (userId) {
        response = await sendPrompt(userId, trimmed)
      } else {
        throw new Error('Authentication required: please register or sign in.')
      }

      const reply = response.reply || ''
      const { isBlocked } = detectFirewallIntercept(reply, response.status)

      const assistantMsg = createChatMessage({
        sender: 'assistant',
        content: reply,
        latency_ms: response.latency_ms,
        status: isBlocked ? 'blocked' : 'success',
        isBlocked: isBlocked,
        level: currentLevel,
      })

      setMessagesByLevel((prev) => {
        const prevList = prev[currentLevel] || []
        const nextList = [...prevList, assistantMsg]
        const nextMap = { ...prev, [currentLevel]: nextList }
        saveChatHistory(nextMap)
        return nextMap
      })

      // Issue #27: footer shows the measured round-trip (null → hidden, the
      // value is never fabricated) and a success clears any error toast.
      setRttMs(response.latencyMs ?? null)
      setNotice(null)
    } catch (err: unknown) {
      // Issue #27: classify the failure for the toast banner & retry policy.
      const feedback = feedbackForFailure(err)

      // Keep the footer RTT in sync when the failure carried a measured latency.
      const measured = (err as { latencyMs?: number | null } | null)?.latencyMs
      if (typeof measured === 'number' && Number.isFinite(measured)) {
        setRttMs(measured)
      }

      const alertText = formatErrorAlert(err)
      const alertMsg = createChatMessage({
        sender: 'system_alert',
        content: alertText,
        status: 'error',
        level: currentLevel,
      })

      setMessagesByLevel((prev) => {
        const prevList = prev[currentLevel] || []
        const nextList = [...prevList, alertMsg]
        const nextMap = { ...prev, [currentLevel]: nextList }
        saveChatHistory(nextMap)
        return nextMap
      })

      // Issue #27: toast banner with the exact copy for this failure kind.
      setNotice({ kind: feedback.kind, text: feedback.notice })

      if (feedback.reenableSubmission) {
        // 502 / network failure: re-enable submission so the user can retry.
        clearCooldown()
        setIsCoolingDown(false)
      } else {
        // 429: keep submission disabled for the full 3-second rate limit window.
        startCooldown()
      }
    } finally {
      setIsLoading(false)
    }
  }, [
    input,
    isCoolingDown,
    isLoading,
    currentLevel,
    onSendPrompt,
    userId,
    startCooldown,
    clearCooldown,
  ])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter without Shift submits
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    // Block input beyond MAX_CHARS
    if (value.length <= MAX_CHARS) {
      setInput(value)
    }
  }

  const charCount = input.length
  const charCounterClass =
    charCount >= MAX_CHARS
      ? 'char-counter char-counter--danger'
      : charCount >= WARN_CHARS
        ? 'char-counter char-counter--warning'
        : 'char-counter'

  // Footer RTT label — only rendered when a real latency was measured.
  const rttLabel = formatRttLabel(rttMs)

  return (
    <section className="chat-terminal">
      {/* Message list */}
      <div className="chat-terminal__messages">
        {currentMessages.length === 0 && !isLoading ? (
          <p className="chat-terminal__empty">
            [ Arena Terminal Ready — Awaiting prompt injection ]
          </p>
        ) : (
          <>
            {currentMessages.map((msg, i) => {
              const content = msg.content || msg.text || ''
              const { isBlocked, isLeak } = detectFirewallIntercept(
                content,
                msg.status
              )
              const blockedActive = isBlocked || Boolean(msg.isBlocked)
              const levelTag = msg.level ?? currentLevel
              const label = getPersonaLabel(
                msg.sender,
                levelTag,
                blockedActive,
                isLeak
              )

              const messageClasses = [
                'chat-message',
                `chat-message--${msg.sender}`,
                blockedActive ? 'chat-message--blocked' : '',
                isLeak ? 'chat-message--leak' : '',
              ]
                .filter(Boolean)
                .join(' ')

              return (
                <div
                  key={msg.id || `${msg.timestamp}-${i}`}
                  className={messageClasses}
                >
                  <div className="chat-message__header">
                    <span className="chat-message__label">{label}</span>
                    <div className="chat-message__badges">
                      {blockedActive && (
                        <span className="chat-message__badge--intercept">
                          ⚠ FIREWALL INTERCEPT
                        </span>
                      )}
                      {isLeak && (
                        <span className="chat-message__badge--leak">
                          ⚠ LEAK MASKED
                        </span>
                      )}
                      {typeof msg.latency_ms === 'number' && msg.latency_ms >= 0 && (
                        <span
                          className="chat-message__latency"
                          title="Inference Latency"
                        >
                          {msg.latency_ms}ms
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="chat-message__text">{content}</div>
                </div>
              )
            })}

            {isLoading && (
              <div className="chat-message chat-message--assistant chat-message--loading">
                <div className="chat-message__header">
                  <span className="chat-message__label">
                    TARGET_BOT [L{currentLevel}]
                  </span>
                </div>
                <div className="chat-message__text chat-typing-indicator">
                  <span className="chat-typing-dots">
                    <span className="chat-typing-dot" />
                    <span className="chat-typing-dot" />
                    <span className="chat-typing-dot" />
                  </span>
                  <span className="chat-typing-cursor">▋</span>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Toast banner — Issue #27: rate limit & gateway failure notices */}
      {notice && (
        <div
          className={`chat-terminal__toast chat-terminal__toast--${notice.kind}`}
          role="status"
          aria-live="polite"
        >
          <span className="chat-terminal__toast-text">{notice.text}</span>
          <button
            type="button"
            className="chat-terminal__toast-dismiss"
            aria-label="Dismiss notification"
            onClick={() => setNotice(null)}
          >
            ×
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="chat-terminal__input-area">
        <div className="chat-terminal__textarea-wrapper">
          <textarea
            ref={textareaRef}
            className="chat-terminal__textarea"
            placeholder="Type injection prompt..."
            rows={3}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            readOnly={isCoolingDown || isLoading}
            maxLength={MAX_CHARS}
          />
          <span className={charCounterClass}>
            {charCount}/{MAX_CHARS}
          </span>
        </div>
        <button
          className={`chat-terminal__submit${isCoolingDown ? ' chat-terminal__submit--cooldown' : ''}`}
          disabled={isCoolingDown || isLoading || charCount === 0}
          onClick={handleSubmit}
        >
          {isCoolingDown ? 'WAIT' : 'SEND'}
        </button>
      </div>

      {/* Terminal footer — Issue #27: request latency from X-Process-Time */}
      <footer className="chat-terminal__footer">
        {rttLabel && (
          <span className="chat-terminal__rtt">{rttLabel}</span>
        )}
      </footer>
    </section>
  )
}
