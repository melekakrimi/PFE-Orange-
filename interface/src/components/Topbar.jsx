export default function Topbar({ client }) {
  const name    = client?.name    || 'Orange Business AI'
  const secteur = client?.secteur || 'Assistant Commercial'
  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()

  return (
    <div className="flex items-center justify-between glass"
      style={{
        padding: '0 24px',
        minHeight: 64,
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        flexShrink: 0,
      }}>

      {/* Left: client info */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center rounded-xl"
          style={{
            width: 38, height: 38,
            background: 'rgba(255,121,0,0.12)',
            border: '1px solid rgba(255,121,0,0.32)',
            fontSize: 12, fontWeight: 600, color: '#FF7900',
            flexShrink: 0,
          }}>
          {initials}
        </div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#F8F8F8', letterSpacing: '-0.02em' }}>
            {name}
          </div>
          <div style={{ fontSize: 11, fontWeight: 300, color: 'rgba(255,255,255,0.35)', marginTop: 1 }}>
            {secteur}
          </div>
        </div>
      </div>

      {/* Right: chips */}
      <div className="flex items-center gap-2">
        {client && (
          <div className="flex items-center gap-1.5 rounded-full"
            style={{
              padding: '5px 12px',
              background: 'rgba(34,197,94,0.10)',
              border: '1px solid rgba(34,197,94,0.25)',
              fontSize: 11, fontWeight: 500, color: '#22C55E',
            }}>
            <span className="rounded-full" style={{ width: 6, height: 6, background: '#22C55E' }} />
            Offre générée
          </div>
        )}
        <div className="rounded-full"
          style={{
            padding: '5px 12px',
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.08)',
            fontSize: 11, fontWeight: 400, color: 'rgba(255,255,255,0.40)',
          }}>
          LLaMA 3.3 70B
        </div>
        <button className="flex items-center justify-center rounded-lg transition-all hover:bg-white/5"
          style={{ width: 34, height: 34, color: 'rgba(255,255,255,0.30)', cursor: 'pointer', border: 'none', background: 'none' }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="3.5" r="1.5" fill="currentColor" />
            <circle cx="8" cy="8"   r="1.5" fill="currentColor" />
            <circle cx="8" cy="12.5" r="1.5" fill="currentColor" />
          </svg>
        </button>
      </div>
    </div>
  )
}