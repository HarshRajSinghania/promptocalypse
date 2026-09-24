import ChatTerminal from './ChatTerminal'

/**
 * ArenaPanel wraps the ChatTerminal in the main content area.
 *
 * The onSendPrompt callback is left unconnected until the API client
 * integration issue is implemented. ChatTerminal works standalone
 * in UI-only mode (messages render locally without backend calls).
 */
export default function ArenaPanel() {
  // TODO: Wire onSendPrompt to API client once auth/session is implemented
  return <ChatTerminal />
}
