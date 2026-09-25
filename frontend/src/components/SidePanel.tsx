import { useEffect, useState } from 'react'
import KeyVault from './KeyVault'
import type { SubmitKeyResponse, LeaderboardEntry } from '../types'
import { fetchLeaderboard } from '../api/client'

interface SidePanelProps {
  onVictory?: (response: SubmitKeyResponse) => void
}

export default function SidePanel({ onVictory }: SidePanelProps) {
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);

  useEffect(() => {
    fetchLeaderboard().then(setLeaderboard).catch(console.error);
    const interval = setInterval(() => {
      fetchLeaderboard().then(setLeaderboard).catch(console.error);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside
      style={{
        flex: '0 0 40%',
        width: '40%',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        padding: '1rem',
        backgroundColor: '#12151f',
        overflowY: 'auto',
      }}
    >
      {/* Mission objective card */}
      <div
        style={{
          backgroundColor: '#1c2132',
          border: '1px solid #262d43',
          borderRadius: '4px',
          padding: '1rem',
        }}
      >
        <h3
          style={{
            color: '#00ff9d',
            fontSize: '0.95rem',
            marginBottom: '0.5rem',
            fontFamily: "'JetBrains Mono', monospace",
            textTransform: 'uppercase',
          }}
        >
          Mission Objective
        </h3>
        <p style={{ color: '#f0f4fc', fontSize: '0.85rem', lineHeight: '1.4' }}>
          Extract the secret key from the defense system without triggering security tripwires.
        </p>
      </div>

      {/* Key submission vault component */}
      <KeyVault onVictory={onVictory} />

      {/* Mini leaderboard placeholder */}
      <div
        style={{
          backgroundColor: '#1c2132',
          border: '1px solid #262d43',
          borderRadius: '4px',
          padding: '1rem',
          flex: 1,
        }}
      >
        <h3
          style={{
            color: '#00ff9d',
            fontSize: '0.95rem',
            marginBottom: '0.5rem',
            fontFamily: "'JetBrains Mono', monospace",
            textTransform: 'uppercase',
          }}
        >
          Mini Leaderboard
        </h3>
        <div style={{ color: '#7983a3', fontSize: '0.85rem', fontFamily: "'JetBrains Mono', monospace" }}>
          {leaderboard.length === 0 ? (
            <p>No entries loaded.</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {leaderboard.map(entry => (
                <li key={entry.username} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', paddingBottom: '0.5rem', borderBottom: '1px solid #262d43' }}>
                  <span>
                    <strong>{entry.rank}. {entry.username}</strong>
                    <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: entry.completed ? '#00ff9d' : '#ffb020', border: `1px solid ${entry.completed ? '#00ff9d' : '#ffb020'}`, padding: '2px 4px', borderRadius: '4px' }}>
                      {entry.status || (entry.completed ? 'Completed' : 'In Progress')}
                    </span>
                  </span>
                  <span>{entry.final_score ?? entry.score} pts</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </aside>
  )
}
