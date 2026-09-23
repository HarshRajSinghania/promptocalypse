import Header from './components/Header.tsx'
import ArenaPanel from './components/ArenaPanel.tsx'
import SidePanel from './components/SidePanel.tsx'

// TODO: Add registration modal gate, session reconciliation
export default function App() {
  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <ArenaPanel />
        <SidePanel />
      </main>
    </div>
  )
}
