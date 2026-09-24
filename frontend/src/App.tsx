import { useState } from 'react'
import Header from './components/Header.tsx'
import ArenaPanel from './components/ArenaPanel.tsx'
import SidePanel from './components/SidePanel.tsx'
import VictoryModal from './components/VictoryModal.tsx'
import type { SubmitKeyResponse } from './types'
import { loadSession } from './utils/session'

export default function App() {
  const [showVictory, setShowVictory] = useState<boolean>(() => {
    const s = loadSession()
    return Boolean(s?.completed)
  })
  const [victoryStats, setVictoryStats] = useState<SubmitKeyResponse['stats'] | null>(null)
  const [finalScore, setFinalScore] = useState<number | null>(() => {
    const s = loadSession()
    return s?.final_score ?? null
  })

  const handleVictory = (res: SubmitKeyResponse) => {
    setShowVictory(true)
    setVictoryStats(res.stats || null)
    setFinalScore(res.final_score ?? null)
  }

  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <ArenaPanel />
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
