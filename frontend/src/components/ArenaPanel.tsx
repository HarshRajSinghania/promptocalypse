import ChatTerminal from './ChatTerminal'
import type { SessionState } from '../types'
import { loadSession } from '../utils/session'
import { sendPrompt } from '../api/client'

interface ArenaPanelProps {
  session?: SessionState | null
}

/**
 * ArenaPanel wraps the ChatTerminal and connects it to the backend chat API.
 */
export default function ArenaPanel({ session }: ArenaPanelProps) {
  const currentSession = session ?? loadSession()
  const userId = currentSession?.user_id || ''
  const currentLevel = currentSession?.current_level || 1

  const handleSendPrompt = async (prompt: string) => {
    if (!userId) {
      throw new Error('Authentication required: please register or sign in.')
    }
    return await sendPrompt(userId, prompt)
  }

  return (
    <ChatTerminal
      userId={userId}
      currentLevel={currentLevel}
      onSendPrompt={handleSendPrompt}
    />
  )
}
