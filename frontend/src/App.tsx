import { useState, useEffect } from 'react'
import Header from './components/Header.tsx'
import ArenaPanel from './components/ArenaPanel.tsx'
import SidePanel from './components/SidePanel.tsx'
import VictoryModal from './components/VictoryModal.tsx'
import RegisterModal from './components/RegisterModal.tsx'
import type { SessionState, SubmitKeyResponse } from './types'
import { loadSession, hasValidSession, SESSION_UPDATE_EVENT } from './utils/session'

export default function App() {
  const [session, setSession] = useState<SessionState | null>(() => {
    return loadSession()
  })
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return hasValidSession()
  })

  useEffect(() => {
    const handleUpdate = (e: Event) => {
      const customEvent = e as CustomEvent<SessionState | null>
      if (customEvent.detail) {
        setSession(customEvent.detail)
        setIsAuthenticated(hasValidSession())
      } else {
        const reloaded = loadSession()
        setSession(reloaded)
        setIsAuthenticated(hasValidSession())
      }
    }
    window.addEventListener(SESSION_UPDATE_EVENT, handleUpdate)
    window.addEventListener('storage', handleUpdate)
    return () => {
      window.removeEventListener(SESSION_UPDATE_EVENT, handleUpdate)
      window.removeEventListener('storage', handleUpdate)
    }
  }, [])
  const [showVictory, setShowVictory] = useState<boolean>(() => {
    const s = loadSession()
    return Boolean(s?.completed)
  })
  const [victoryStats, setVictoryStats] = useState<SubmitKeyResponse['stats'] | null>(null)
  const [finalScore, setFinalScore] = useState<number | null>(() => {
    const s = loadSession()
    return s?.final_score ?? null
  })

  const handleAuthenticated = (newSession: SessionState) => {
    setSession(newSession)
    setIsAuthenticated(true)
    if (newSession.completed) {
      setShowVictory(true)
    }
  }

  const handleVictory = (res: SubmitKeyResponse) => {
    setShowVictory(true)
    setVictoryStats(res.stats || null)
    setFinalScore(res.final_score ?? null)
  }

  return (
    <div className="app-container">
      {!isAuthenticated && (
        <RegisterModal onSuccess={handleAuthenticated} />
      )}
      <Header session={session} />
      <main className="main-content">
        <ArenaPanel session={session} />
        <SidePanel onVictory={handleVictory} />
      </main>
      {showVictory && (
        <VictoryModal
          isOpen={showVictory}
          onClose={() => setShowVictory(false)}
          stats={victoryStats}
          finalScore={finalScore}
        />
      )}
    </div>
  )
}
