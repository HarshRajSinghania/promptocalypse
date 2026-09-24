import confetti from 'canvas-confetti'

/**
 * Triggers a multi-burst cyberpunk confetti shower upon completing Level 3.
 */
export function triggerVictoryConfetti(): void {
  const duration = 3000
  const end = Date.now() + duration

  const colors = ['#00ff9d', '#00e5ff', '#ff3b5c', '#ffb020', '#ffffff']

  // Initial burst from center
  confetti({
    particleCount: 80,
    spread: 100,
    origin: { y: 0.6 },
    colors,
  })

  // Continuous side cannons for 3 seconds
  const frame = () => {
    confetti({
      particleCount: 4,
      angle: 60,
      spread: 55,
      origin: { x: 0, y: 0.7 },
      colors,
    })
    confetti({
      particleCount: 4,
      angle: 120,
      spread: 55,
      origin: { x: 1, y: 0.7 },
      colors,
    })

    if (Date.now() < end) {
      requestAnimationFrame(frame)
    }
  }

  frame()
}
