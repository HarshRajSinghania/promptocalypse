// TODO: Implement registration flow, localStorage persistence
export default function RegisterModal() {
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
          border: '1px solid #262d43',
          borderRadius: '6px',
          padding: '2rem',
          width: '100%',
          maxWidth: '400px',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        <h2
          style={{
            color: '#00ff9d',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '1.25rem',
            margin: 0,
          }}
        >
          Join Arena
        </h2>
        <input
          type="text"
          placeholder="Enter username"
          style={{
            backgroundColor: '#0a0b10',
            color: '#f0f4fc',
            border: '1px solid #262d43',
            borderRadius: '4px',
            padding: '0.75rem',
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
            padding: '0.75rem',
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 'bold',
            cursor: 'pointer',
          }}
        >
          Enter Arena
        </button>
      </div>
    </div>
  )
}
