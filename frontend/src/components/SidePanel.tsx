// TODO: Wire up key submission, leaderboard polling
export default function SidePanel() {
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

      {/* Key submission card */}
      <div
        style={{
          backgroundColor: '#1c2132',
          border: '1px solid #262d43',
          borderRadius: '4px',
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}
      >
        <h3
          style={{
            color: '#00ff9d',
            fontSize: '0.95rem',
            marginBottom: '0.25rem',
            fontFamily: "'JetBrains Mono', monospace",
            textTransform: 'uppercase',
          }}
        >
          Vault Key Submission
        </h3>
        <input
          type="text"
          placeholder="FLAG{...}"
          style={{
            backgroundColor: '#0a0b10',
            color: '#f0f4fc',
            border: '1px solid #262d43',
            borderRadius: '4px',
            padding: '0.5rem 0.75rem',
            fontFamily: "'JetBrains Mono', monospace",
            outline: 'none',
          }}
        />
        <button
          style={{
            backgroundColor: '#00ff9d',
            color: '#0a0b10',
            border: 'none',
            borderRadius: '4px',
            padding: '0.5rem',
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 'bold',
            cursor: 'pointer',
          }}
        >
          Verify Key
        </button>
      </div>

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
          <p>No entries loaded.</p>
        </div>
      </div>
    </aside>
  )
}
