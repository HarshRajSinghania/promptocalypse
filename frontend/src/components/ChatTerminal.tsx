import { useState, useRef, useEffect, useCallback } from 'react'
import type { ChatMessage } from '../types'
import {
  COOLDOWN_MS,
  NOTICE_DISMISS_MS,
  feedbackForFailure,
  formatRttLabel,
  type ChatFailureKind,
} from '../utils/chatFeedback'
import './ChatTerminal.css'

const MAX_CHARS = 1000
const WARN_CHARS = 900

interface ChatTerminalProps {
  /**
   * Callback to send a prompt to the backend.
   * Returns the bot reply text, optional status ('blocked' for firewall
   * intercepts) and the measured round-trip time from X-Process-Time.
   */
  onSendPrompt?: (prompt: string) => Promise<{
    reply: string
    status?: string
    latencyMs?: number | null
  }>
}

interface ChatNotice {
  kind: ChatFailureKind
  text: string
}

export default function ChatTerminal({ onSendPrompt }: ChatTerminalProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isCoolingDown, setIsCoolingDown] = useState(false)
  const [notice, setNotice] = useState<ChatNotice | null>(null)
  const [rttMs, setRttMs] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const cooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
    if (!trimmed || isCoolingDown) return

    // Add user message
    const userMsg: ChatMessage = {
      sender: 'user',
      text: trimmed,
      timestamp: Date.now(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')

    // Start cooldown
    startCooldown()

    // Send to backend if callback provided
    if (onSendPrompt) {
      try {
        const response = await onSendPrompt(trimmed)
        const botMsg: ChatMessage = {
          sender: response.status === 'blocked' ? 'system' : 'bot',
          text: response.reply,
          timestamp: Date.now(),
          isBlocked: response.status === 'blocked',
        }
        setMessages((prev) => [...prev, botMsg])
        setRttMs(response.latencyMs ?? null)
        setNotice(null)
      } catch (error) {
        const feedback = feedbackForFailure(error)

        // Keep the footer RTT in sync when the failure carried a measured latency.
        const measured = (error as { latencyMs?: number | null } | null)
          ?.latencyMs
        if (typeof measured === 'number' && Number.isFinite(measured)) {
          setRttMs(measured)
        }

        const errorMsg: ChatMessage = {
          sender: 'system',
          text: feedback.notice,
          timestamp: Date.now(),
        }
        setMessages((prev) => [...prev, errorMsg])
        setNotice({ kind: feedback.kind, text: feedback.notice })

        if (feedback.reenableSubmission) {
          // 502 / network failure: re-enable submission so the user can retry.
          clearCooldown()
          setIsCoolingDown(false)
        } else {
          // 429: keep submission disabled for the full 3-second rate limit window.
          startCooldown()
        }
      }
    }
  }, [input, isCoolingDown, onSendPrompt, startCooldown, clearCooldown])

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
        {messages.length === 0 ? (
          <p className="chat-terminal__empty">
            [ Arena Terminal Ready — Awaiting prompt injection ]
          </p>
        ) : (
          messages.map((msg, i) => (
            <div
              key={`${msg.timestamp}-${i}`}
              className={`chat-message chat-message--${msg.sender}${msg.isBlocked ? ' chat-message--blocked' : ''}`}
            >
              <span className="chat-message__label">
                {msg.sender === 'user'
                  ? '> YOU'
                  : msg.sender === 'bot'
                    ? '< BOT'
                    : '⚠ FIREWALL'}
              </span>
              <span className="chat-message__text">{msg.text}</span>
            </div>
          ))
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
            readOnly={isCoolingDown}
            maxLength={MAX_CHARS}
          />
          <span className={charCounterClass}>
            {charCount}/{MAX_CHARS}
          </span>
        </div>
        <button
          className={`chat-terminal__submit${isCoolingDown ? ' chat-terminal__submit--cooldown' : ''}`}
          disabled={isCoolingDown || charCount === 0}
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
