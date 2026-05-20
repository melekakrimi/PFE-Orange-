import { useState, useRef } from 'react'

const IconSend = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M14 2L8.5 7.5M14 2L10 14L8.5 7.5L2 5.5L14 2Z"
      stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

export default function InputZone({ onSend }) {
  const [value, setValue]     = useState('')
  const [focused, setFocused] = useState(false)
  const textareaRef           = useRef(null)

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed) return
    onSend(trimmed)
    setValue('')
    setTimeout(() => textareaRef.current?.focus(), 50)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const canSend = value.trim().length > 0

  return (
    <div style={{
      padding: '14px 24px 18px',
      background: 'rgba(12,12,14,0.88)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      borderTop: '1px solid rgba(255,255,255,0.06)',
      flexShrink: 0,
    }}>
      <div style={{ maxWidth: 760, margin: '0 auto' }}>

        {/* Textarea wrapper */}
        <div style={{
          position: 'relative',
          background: 'rgba(255,255,255,0.04)',
          border: `1px solid ${focused ? 'rgba(255,121,0,0.52)' : 'rgba(255,255,255,0.09)'}`,
          borderRadius: 16,
          boxShadow: focused ? '0 0 0 3px rgba(255,121,0,0.09)' : 'none',
          transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
        }}>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            rows={3}
            placeholder="Décrivez le profil du client — secteur, taille, besoins en Fibre et/ou Microsoft 365..."
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              outline: 'none',
              padding: '16px 16px 48px',
              fontSize: 13.5,
              fontFamily: 'Inter, sans-serif',
              fontWeight: 400,
              lineHeight: 1.6,
              letterSpacing: '-0.01em',
              color: 'rgba(255,255,255,0.85)',
              resize: 'none',
            }}
          />

          {/* Bottom toolbar */}
          <div style={{
            position: 'absolute', bottom: 0, left: 0, right: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0 12px 10px',
          }}>
            {/* Left: shortcuts + icons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {/* Keyboard shortcuts */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: 'rgba(255,255,255,0.22)' }}>
                <kbd style={{
                  padding: '2px 6px', borderRadius: 5,
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.10)',
                  color: 'rgba(255,255,255,0.30)',
                  fontSize: 10, fontFamily: 'inherit',
                }}>⏎</kbd>
                <span>envoyer</span>
                <span style={{ opacity: 0.4, margin: '0 2px' }}>·</span>
                <kbd style={{
                  padding: '2px 6px', borderRadius: 5,
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.10)',
                  color: 'rgba(255,255,255,0.30)',
                  fontSize: 10, fontFamily: 'inherit',
                }}>⇧⏎</kbd>
                <span>nouvelle ligne</span>
              </div>

            </div>

            {/* Send button */}
            <button
              onClick={handleSend}
              disabled={!canSend}
              className={`flex items-center justify-center rounded-xl ${canSend ? 'glow-btn' : ''}`}
              style={{
                width: 42, height: 42,
                background: canSend
                  ? 'linear-gradient(135deg,#FF7900,#FF4500)'
                  : 'rgba(255,255,255,0.06)',
                border: 'none',
                cursor: canSend ? 'pointer' : 'not-allowed',
                opacity: canSend ? 1 : 0.35,
                flexShrink: 0,
                transition: 'all 0.2s ease',
              }}>
              <IconSend />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
