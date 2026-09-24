import { useState, useRef, useEffect, useCallback } from 'react'
import type { ChatMessage } from '../types'
import './ChatTerminal.css'

const MAX_CHARS = 1000
const WARN_CHARS = 900
const COOLDOWN_MS = 3000

interface ChatTerminalProps {
  /**
   * Callback to send a prompt to the backend.
   * Returns the bot reply text and optional status ('blocked' for firewall intercepts).
   */
  onSendPrompt?: (prompt: string) => Promise<{ reply: string; status?: string }>
}

export default function ChatTerminal({ onSendPrompt }: ChatTerminalProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isCoolingDown, setIsCoolingDown] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
    setIsCoolingDown(true)
    setTimeout(() => setIsCoolingDown(false), COOLDOWN_MS)

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
      } catch {
        const errorMsg: ChatMessage = {
          sender: 'system',
          text: '[ Connection error — retry after cooldown ]',
          timestamp: Date.now(),
        }
        setMessages((prev) => [...prev, errorMsg])
      }
    }
  }, [input, isCoolingDown, onSendPrompt])

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
    </section>
  )
}
