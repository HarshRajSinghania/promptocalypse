import { useState, useRef, useEffect, useCallback } from 'react'
import type { ChatMessage } from '../types'
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
const COOLDOWN_MS = 3000

export interface ChatTerminalProps {
  userId?: string
  currentLevel?: number
  /**
   * Callback to send a prompt to the backend.
   * Returns the bot reply text, optional status ('blocked'), latency_ms, cooldown_seconds.
   */
  onSendPrompt?: (prompt: string) => Promise<{
    reply: string
    status?: string
    latency_ms?: number
    cooldown_seconds?: number
  }>
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
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const currentMessages = messagesByLevel[currentLevel] || []

  // Auto-scroll to bottom when messages, loading state, or current level changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [currentMessages, isLoading, currentLevel])

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

    // 2. Start 3-second visual cooldown
    setIsCoolingDown(true)
    setTimeout(() => setIsCoolingDown(false), COOLDOWN_MS)

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
    } catch (err: unknown) {
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
    } finally {
      setIsLoading(false)
    }
  }, [input, isCoolingDown, isLoading, currentLevel, onSendPrompt, userId])

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
    </section>
  )
}
