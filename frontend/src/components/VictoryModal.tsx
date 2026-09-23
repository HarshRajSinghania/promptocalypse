// TODO: Implement score display, confetti, leaderboard link
export default function VictoryModal() {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(10, 11, 16, 0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
      }}
    >
      <div
        style={{
          backgroundColor: '#12151f',
          border: '1px solid #00ff9d',
          borderRadius: '6px',
          padding: '2rem',
          width: '100%',
          maxWidth: '450px',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          fontFamily: "'JetBrains Mono', monospace",
        }}
      >
        <h2 style={{ color: '#00ff9d', margin: 0, textAlign: 'center' }}>
          SYSTEM COMPROMISED
        </h2>
        <p style={{ color: '#7983a3', textAlign: 'center', fontSize: '0.9rem' }}>
          Victory! All defense layers breached.
        </p>
        <div
          style={{
            backgroundColor: '#1c2132',
            padding: '1rem',
            borderRadius: '4px',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
            fontSize: '0.85rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#7983a3' }}>Base Score:</span>
            <span>1,000 pts</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#7983a3' }}>Time Penalty:</span>
            <span style={{ color: '#ff3b5c' }}>-120 pts</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#7983a3' }}>Prompt Penalties:</span>
            <span style={{ color: '#ff3b5c' }}>-50 pts</span>
          </div>
          <hr style={{ borderColor: '#262d43', margin: '0.25rem 0' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold' }}>
            <span style={{ color: '#f0f4fc' }}>Final Score:</span>
            <span style={{ color: '#00ff9d' }}>830 pts</span>
          </div>
        </div>
      </div>
    </div>
  )
}
