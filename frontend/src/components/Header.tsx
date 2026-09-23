// TODO: Wire up live metrics from game state
export default function Header() {
  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.75rem 1.5rem',
        backgroundColor: '#12151f',
        borderBottom: '1px solid #262d43',
        fontFamily: "'JetBrains Mono', monospace",
        color: '#f0f4fc',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <span style={{ color: '#00ff9d', fontWeight: 'bold', fontSize: '1.1rem' }}>
          AI Jailbreak Arena
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', fontSize: '0.9rem' }}>
        <div>
          <span style={{ color: '#7983a3' }}>LEVEL: </span>
          <span style={{ color: '#00ff9d' }}>1 / 3</span>
        </div>
        <div>
          <span style={{ color: '#7983a3' }}>TIME: </span>
          <span>00:00</span>
        </div>
        <div>
          <span style={{ color: '#7983a3' }}>PROMPTS: </span>
          <span>0</span>
        </div>
        <div>
          <span style={{ color: '#7983a3' }}>SCORE: </span>
          <span style={{ color: '#00ff9d' }}>1000</span>
        </div>
      </div>
    </header>
  )
}
