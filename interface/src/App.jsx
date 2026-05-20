import { useState } from 'react'
import Sidebar   from './components/Sidebar'
import Topbar    from './components/Topbar'
import ChatArea  from './components/ChatArea'
import InputZone from './components/InputZone'
import useChat   from './hooks/useChat'

export default function App() {
  const { messages, isTyping, activeClient, localHistory, sendMessage, loadProposition } = useChat()
  const [activeConv, setActiveConv] = useState(null)

  const handleLoadProposition = (data) => {
    if (!data) {
      loadProposition(null)   // nouvelle offre → réinitialise
    } else {
      loadProposition(data)
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden relative" style={{ background: '#0C0C0E' }}>

      {/* Background orbs */}
      <div className="fixed inset-0 overflow-hidden" style={{ zIndex: 0, pointerEvents: 'none' }}>
        <div className="orb-1 absolute rounded-full"
          style={{ top: '-8%', left: '-6%', width: 420, height: 420,
            background: 'radial-gradient(circle, rgba(255,121,0,0.22) 0%, transparent 68%)',
            filter: 'blur(55px)' }} />
        <div className="orb-2 absolute rounded-full"
          style={{ bottom: '-10%', right: '-6%', width: 360, height: 360,
            background: 'radial-gradient(circle, rgba(255,69,0,0.18) 0%, transparent 68%)',
            filter: 'blur(60px)' }} />
        <div className="orb-3 absolute rounded-full"
          style={{ top: '38%', right: '28%', width: 280, height: 280,
            background: 'radial-gradient(circle, rgba(255,121,0,0.10) 0%, transparent 68%)',
            filter: 'blur(80px)' }} />
      </div>

      {/* Grid overlay */}
      <div className="grid-overlay fixed inset-0" style={{ zIndex: 0 }} />

      {/* Sidebar */}
      <div style={{ position: 'relative', zIndex: 10 }}>
        <Sidebar
          activeConv={activeConv}
          setActiveConv={setActiveConv}
          onLoadProposition={handleLoadProposition}
          localHistory={localHistory}
        />
      </div>

      {/* Main area */}
      <div className="flex flex-col flex-1 overflow-hidden" style={{ position: 'relative', zIndex: 10 }}>
        <Topbar client={activeClient} />
        <ChatArea messages={messages} isTyping={isTyping} />
        <InputZone onSend={sendMessage} />
      </div>
    </div>
  )
}