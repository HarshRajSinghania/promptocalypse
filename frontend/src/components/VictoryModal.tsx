import { useEffect } from 'react'
import { loadSession, calculatePromptPenalty, formatElapsedTime } from '../utils/session'
import { triggerVictoryConfetti } from '../utils/confetti'
import './VictoryModal.css'

interface VictoryModalProps {
  isOpen?: boolean
  onClose?: () => void
  finalScore?: number | null
  stats?: {
    total_prompts: number
    elapsed_minutes?: number
    failed_attempts: number
  } | null
}

export default function VictoryModal({
  isOpen = true,
  onClose,
  finalScore: propScore,
  stats: propStats,
}: VictoryModalProps) {
  const session = loadSession()

  useEffect(() => {
    if (isOpen) {
      triggerVictoryConfetti()
    }
  }, [isOpen])

  if (!isOpen) return null

  const prompts = propStats?.total_prompts ?? session?.total_prompts ?? 0
  const fails = propStats?.failed_attempts ?? session?.failed_attempts ?? 0

  let elapsedMinutes = propStats?.elapsed_minutes
  if (typeof elapsedMinutes !== 'number' && session?.start_time) {
    const startMs = new Date(session.start_time).getTime()
    elapsedMinutes = Math.floor(Math.max(0, (Date.now() - startMs) / 1000) / 60)
  }
  elapsedMinutes = elapsedMinutes ?? 0

  const promptPenalty = calculatePromptPenalty(prompts)
  const timePenalty = elapsedMinutes * 2
  const failPenalty = fails * 25

  const finalScore =
    propScore ??
    session?.final_score ??
    Math.max(0, 1000 - promptPenalty - timePenalty - failPenalty)

  return (
    <div className="victory-backdrop" role="dialog" aria-modal="true">
      <div className="victory-modal">
        <h2 className="victory-title">SYSTEM COMPROMISED</h2>
        <p className="victory-subtitle">
          Victory! All defense layers successfully breached.
        </p>

        <div className="victory-breakdown">
          {/* Base Points */}
          <div className="victory-row">
            <span className="victory-row__label">Base Score:</span>
            <span className="victory-row__val">1,000 pts</span>
          </div>

          {/* Prompts Used */}
          <div className="victory-row">
            <span className="victory-row__label">Prompts Used:</span>
            <span className="victory-row__val">
              {prompts}
              {promptPenalty > 0 && (
                <span className="victory-row__val--penalty">
                  {' '}
                  (-{promptPenalty} pts)
                </span>
              )}
            </span>
          </div>

          {/* Time Elapsed */}
          <div className="victory-row">
            <span className="victory-row__label">Time Elapsed:</span>
            <span className="victory-row__val">
              {formatElapsedTime(elapsedMinutes * 60)}
              {timePenalty > 0 && (
                <span className="victory-row__val--penalty">
                  {' '}
                  (-{timePenalty} pts)
                </span>
              )}
            </span>
          </div>

          {/* Failed Attempts */}
          <div className="victory-row">
            <span className="victory-row__label">Failed Attempts:</span>
            <span className="victory-row__val">
              {fails}
              {failPenalty > 0 && (
                <span className="victory-row__val--penalty">
                  {' '}
                  (-{failPenalty} pts)
                </span>
              )}
            </span>
          </div>

          <hr className="victory-divider" />

          {/* Final Score */}
          <div className="victory-score-row">
            <span>FINAL SCORE:</span>
            <span className="victory-score-val">
              {Math.round(finalScore)} PTS
            </span>
          </div>
        </div>

        <button
          className="victory-btn"
          onClick={onClose}
          autoFocus
        >
          Review Leaderboard & Telemetry
        </button>
      </div>
    </div>
  )
}
