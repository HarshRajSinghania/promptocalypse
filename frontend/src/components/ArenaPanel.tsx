// TODO: Implement chat logic, cooldown timer, character counter
export default function ArenaPanel() {
  return (
    <section
      style={{
        flex: '0 0 60%',
        width: '60%',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        borderRight: '1px solid #262d43',
        backgroundColor: '#0a0b10',
      }}
    >
      {/* Chat message list area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          color: '#7983a3',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.9rem',
        }}
      >
        <p>[ Arena Terminal Ready - Awaiting prompt injection ]</p>
      </div>

      {/* Input area */}
      <div
        style={{
          padding: '1rem',
          borderTop: '1px solid #262d43',
          backgroundColor: '#12151f',
          display: 'flex',
          gap: '0.75rem',
        }}
      >
        <textarea
          placeholder="Type injection prompt..."
          rows={3}
          style={{
            flex: 1,
            backgroundColor: '#0a0b10',
            color: '#f0f4fc',
            border: '1px solid #262d43',
            borderRadius: '4px',
            padding: '0.5rem 0.75rem',
            fontFamily: "'JetBrains Mono', monospace",
            resize: 'none',
            outline: 'none',
          }}
        />
        <button
          disabled
          style={{
            backgroundColor: '#1c2132',
            color: '#7983a3',
            border: '1px solid #262d43',
            borderRadius: '4px',
            padding: '0 1.25rem',
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 'bold',
            cursor: 'not-allowed',
          }}
        >
          Send
        </button>
      </div>
    </section>
  )
}
