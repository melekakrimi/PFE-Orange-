import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'

const WELCOME = {
  role: 'ai',
  id:   'welcome',
  content:
    "Bonjour ! Je suis l'assistant commercial Orange Business Tunisie. " +
    "Décrivez-moi le profil de votre client — entreprise, secteur d'activité, " +
    "besoins en Fibre Optique et/ou Microsoft 365 — et je génère une proposition " +
    "commerciale complète avec PPTX, Word et PDF en quelques secondes.",
  agentTimes: null,
  result:     null,
}

function TypingIndicator() {
  return (
    <div className="anim-fadeUp flex gap-3" style={{ alignItems: 'flex-start' }}>
      <div className="flex items-center justify-center rounded-xl"
        style={{ width: 34, height: 34, background: 'linear-gradient(135deg,#FF7900,#FF4500)', flexShrink: 0, marginTop: 2 }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9"   stroke="white" strokeWidth="2.2" />
          <circle cx="12" cy="12" r="4.5" fill="white" />
        </svg>
      </div>
      <div className="flex items-center gap-1.5"
        style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          backdropFilter: 'blur(20px)',
          borderRadius: '4px 16px 16px 16px',
          padding: '14px 18px',
        }}>
        {[0, 1, 2].map(i => (
          <span key={i} className="typing-dot rounded-full"
            style={{ width: 7, height: 7, background: '#FF7900', display: 'block' }} />
        ))}
      </div>
    </div>
  )
}

export default function ChatArea({ messages, isTyping }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  return (
    <div className="flex-1 overflow-y-auto"
      style={{ padding: '28px 24px 16px' }}>
      <div style={{ maxWidth: 760, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 22 }}>
        <MessageBubble message={WELCOME} />
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
