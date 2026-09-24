import { useState, useEffect, useMemo } from 'react'
import type { SessionState } from '../types'
import {
  calculateDynamicScore,
  calculatePromptPenalty,
  formatElapsedTime,
  loadSession,
  getOrCreateDefaultSession,
  SESSION_UPDATE_EVENT,
} from '../utils/session'
import './Header.css'

interface HeaderProps {
  /** Optional external session override (e.g. from parent state/context) */
  session?: SessionState | null
}

export default function Header({ session: propSession }: HeaderProps) {
  // Load and recover session from localStorage (th_session_v1)
  const [internalSession, setInternalSession] = useState<SessionState>(() => {
    return propSession || loadSession() || getOrCreateDefaultSession()
  })

  // Synchronize if prop changes
  useEffect(() => {
    if (propSession) {
      setInternalSession(propSession)
    }
  }, [propSession])

  // Listen for session updates (same-tab and multi-tab sync)
  useEffect(() => {
    const handleLocalUpdate = (e: Event) => {
      const customEvent = e as CustomEvent<SessionState | null>
      if (customEvent.detail) {
        setInternalSession(customEvent.detail)
      } else {
        setInternalSession(getOrCreateDefaultSession())
      }
    }

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'th_session_v1') {
        const reloaded = loadSession()
        if (reloaded) {
          setInternalSession(reloaded)
        }
      }
    }

    window.addEventListener(SESSION_UPDATE_EVENT, handleLocalUpdate)
    window.addEventListener('storage', handleStorageChange)
    return () => {
      window.removeEventListener(SESSION_UPDATE_EVENT, handleLocalUpdate)
      window.removeEventListener('storage', handleStorageChange)
    }
  }, [])

  const currentLevel = internalSession.current_level ?? 1
  const completed = Boolean(internalSession.completed)
  const totalPrompts = internalSession.total_prompts ?? 0
  const failedAttempts = internalSession.failed_attempts ?? 0

  // ── Stopwatch Timer counting elapsed time from start_time ──
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(() => {
    if (!internalSession.start_time) return 0
    const startMs = new Date(internalSession.start_time).getTime()
    return Math.max(0, Math.floor((Date.now() - startMs) / 1000))
  })

  useEffect(() => {
    // If completed or start_time is missing, don't run the ticker
    if (completed || !internalSession.start_time) {
      return
    }

    const startMs = new Date(internalSession.start_time).getTime()
    // Recalculate immediately
    setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startMs) / 1000)))

    const timer = setInterval(() => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startMs) / 1000)))
    }, 1000)

    return () => clearInterval(timer)
  }, [internalSession.start_time, completed])

  // ── Dynamic Score & Prompt Penalty Calculations ──
  const promptPenalty = useMemo(
    () => calculatePromptPenalty(totalPrompts),
    [totalPrompts]
  )

  const dynamicScore = useMemo(() => {
    if (completed && typeof internalSession.final_score === 'number') {
      return internalSession.final_score
    }
    return calculateDynamicScore({
      prompts: totalPrompts,
      elapsedSeconds,
      failedAttempts,
    })
  }, [
    completed,
    internalSession.final_score,
    totalPrompts,
    elapsedSeconds,
    failedAttempts,
  ])

  // ── Step Indicator Configurations ──
  const levels = [1, 2, 3]

  return (
    <header className="hud-header">
      {/* Brand & Participant Identity */}
      <div className="hud-brand">
        <span className="hud-logo">AI Jailbreak Arena</span>
        {internalSession.username && (
          <span
            className="hud-user-badge"
            title={internalSession.email ? `Email: ${internalSession.email}` : undefined}
          >
            AGENT: <strong>{internalSession.username}</strong>
            {internalSession.email && (
              <span style={{ opacity: 0.7, marginLeft: '0.35rem', fontSize: '0.7rem' }}>
                ({internalSession.email})
              </span>
            )}
          </span>
        )}
      </div>

      {/* Segmented Step Indicator: Level 1, 2, 3 */}
      <nav aria-label="Level Progress" className="hud-steps">
        {levels.map((lvl) => {
          const isCompleted = completed || currentLevel > lvl
          const isActive = !completed && currentLevel === lvl
          const isLocked = !completed && currentLevel < lvl

          let stepClass = 'hud-step'
          let icon = '🔒'
          let ariaStatus = 'Locked'

          if (isCompleted) {
            stepClass += ' hud-step--completed'
            icon = '✓'
            ariaStatus = 'Completed'
          } else if (isActive) {
            stepClass += ' hud-step--active'
            icon = '●'
            ariaStatus = 'Active'
          } else if (isLocked) {
            stepClass += ' hud-step--locked'
            icon = '🔒'
            ariaStatus = 'Locked'
          }

          return (
            <div
              key={lvl}
              className={stepClass}
              title={`Level ${lvl}: ${ariaStatus}`}
              aria-current={isActive ? 'step' : undefined}
            >
              <span className="hud-step__icon">{icon}</span>
              <span className="hud-step__label">LVL {lvl}</span>
            </div>
          )
        })}
      </nav>

      {/* Live Telemetry Bar */}
      <div className="hud-telemetry">
        {/* Stopwatch Timer */}
        <div className="hud-metric">
          <span className="hud-metric__label">TIME:</span>
          <span className="hud-metric__value hud-metric__value--time">
            {formatElapsedTime(elapsedSeconds)}
          </span>
        </div>

        {/* Dynamic Prompt Count & Penalty Counter */}
        <div className="hud-metric">
          <span className="hud-metric__label">PROMPTS:</span>
          <span className="hud-metric__value">
            {totalPrompts}
            <span
              className={`hud-metric__penalty${promptPenalty > 0 ? ' hud-metric__penalty--active' : ''}`}
            >
              (-{promptPenalty} pts)
            </span>
          </span>
        </div>

        {/* Dynamic Live Score */}
        <div className="hud-metric">
          <span className="hud-metric__label">SCORE:</span>
          <span
            className={`hud-metric__value hud-metric__value--score${
              dynamicScore <= 500
                ? ' hud-metric__value--score-danger'
                : dynamicScore <= 800
                  ? ' hud-metric__value--score-warning'
                  : ''
            }`}
          >
            {Math.round(dynamicScore)}
          </span>
        </div>
      </div>
    </header>
  )
}
