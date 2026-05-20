import { useState, useEffect } from 'react'

const OrangeLogo = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="9"   stroke="white" strokeWidth="2.2" />
    <circle cx="12" cy="12" r="4.5" fill="white" />
  </svg>
)

const TAG = {
  orange: { bg: 'rgba(255,121,0,0.14)',  bd: 'rgba(255,121,0,0.30)',  tx: '#FF7900' },
  teal:   { bg: 'rgba(20,184,166,0.12)', bd: 'rgba(20,184,166,0.28)', tx: '#14B8A6' },
  purple: { bg: 'rgba(139,92,246,0.12)', bd: 'rgba(139,92,246,0.28)', tx: '#A78BFA' },
}

function Tag({ label, color }) {
  const s = TAG[color]
  return (
    <span style={{
      fontSize: 9, fontWeight: 600, padding: '2px 5px', borderRadius: 5,
      background: s.bg, border: `1px solid ${s.bd}`, color: s.tx,
    }}>
      {label}
    </span>
  )
}

function groupByDate(items) {
  const today     = new Date(); today.setHours(0,0,0,0)
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1)
  const weekAgo   = new Date(today); weekAgo.setDate(today.getDate() - 7)

  const groups = { "Aujourd'hui": [], "Hier": [], "Cette semaine": [], "Plus ancien": [] }

  items.forEach(item => {
    const d = new Date(item.created_at); d.setHours(0,0,0,0)
    if (d >= today)          groups["Aujourd'hui"].push(item)
    else if (d >= yesterday) groups["Hier"].push(item)
    else if (d >= weekAgo)   groups["Cette semaine"].push(item)
    else                     groups["Plus ancien"].push(item)
  })

  return Object.entries(groups).filter(([, v]) => v.length > 0)
}

function formatTime(dateStr) {
  const d = new Date(dateStr)
  const today = new Date(); today.setHours(0,0,0,0)
  const itemDay = new Date(d); itemDay.setHours(0,0,0,0)

  if (itemDay >= today) {
    return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}

function buildTitle(item) {
  const parts = [item.entreprise]
  const details = []
  if (item.a_fibre)     details.push('Fibre')
  if (item.a_microsoft) details.push(item.plan_recommande?.replace('Microsoft 365 ', 'MS ') || 'MS365')
  if (details.length)   parts.push(details.join(' + '))
  return parts.join(' — ')
}

export default function Sidebar({ activeConv, setActiveConv, onLoadProposition, localHistory = [] }) {
  const [dbHistory, setDbHistory] = useState([])
  const [loading,   setLoading]   = useState(true)

  const fetchHistory = async () => {
    try {
      const res = await fetch('/history')
      if (res.ok) setDbHistory(await res.json())
    } catch {
      // DB non disponible — on utilise uniquement localHistory
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchHistory() }, [])

  useEffect(() => {
    const handler = () => fetchHistory()
    window.addEventListener('refresh-history', handler)
    return () => window.removeEventListener('refresh-history', handler)
  }, [])

  const handleClick = async (item) => {
    setActiveConv(item.id)
    if (!onLoadProposition) return

    // Item local (session en mémoire) → on a déjà le result
    if (item.result) {
      onLoadProposition(item.result)
      return
    }

    // Item DB → on va chercher le détail
    try {
      const res = await fetch(`/proposition/${item.id}`)
      if (res.ok) onLoadProposition(await res.json())
    } catch {}
  }

  // Fusion : local en premier, puis DB (sans doublons sur entreprise+date)
  const dbIds = new Set(dbHistory.map(d => d.id))
  const merged = [
    ...localHistory,
    ...dbHistory.filter(d => !localHistory.some(l => l.id === d.id)),
  ]

  const grouped = groupByDate(merged)

  return (
    <div className="flex flex-col h-full glass"
      style={{ width: 260, minWidth: 260, borderRight: '1px solid rgba(255,255,255,0.06)' }}>

      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center justify-center rounded-[10px]"
          style={{ width: 40, height: 40, background: 'linear-gradient(135deg,#FF7900,#FF4500)', flexShrink: 0 }}>
          <OrangeLogo />
        </div>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: '#F8F8F8', letterSpacing: '-0.02em' }}>
            Orange Business AI
          </div>
          <div style={{ fontSize: 11, fontWeight: 300, color: 'rgba(255,255,255,0.35)', marginTop: 2, letterSpacing: '0.03em' }}>
            Commercial Platform
          </div>
        </div>
      </div>

      {/* Nouvelle offre */}
      <div style={{ padding: '12px 16px' }}>
        <button
          onClick={() => { setActiveConv(null); onLoadProposition && onLoadProposition(null) }}
          className="w-full flex items-center justify-center gap-2 rounded-xl transition-all duration-150 hover:opacity-80"
          style={{
            padding: '10px 0',
            background: 'rgba(255,121,0,0.07)',
            border: '1px solid rgba(255,121,0,0.38)',
            color: '#FF7900', fontSize: 13, fontWeight: 500, cursor: 'pointer',
          }}>
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M6.5 1v11M1 6.5h11" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          </svg>
          Nouvelle offre
        </button>
      </div>

      {/* History */}
      <div className="flex-1 overflow-y-auto" style={{ padding: '4px 12px' }}>

        {loading && (
          <div style={{ textAlign: 'center', padding: '20px 0', fontSize: 11,
            color: 'rgba(255,255,255,0.25)' }}>
            Chargement...
          </div>
        )}

        {!loading && merged.length === 0 && (
          <div style={{ textAlign: 'center', padding: '24px 12px', fontSize: 12,
            color: 'rgba(255,255,255,0.22)', lineHeight: 1.6 }}>
            Aucune offre générée.<br />
            Commencez par décrire un client.
          </div>
        )}

        {grouped.map(([group, items]) => (
          <div key={group} style={{ marginBottom: 20 }}>
            <div style={{
              fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.22)',
              textTransform: 'uppercase', letterSpacing: '0.1em',
              padding: '0 8px', marginBottom: 6,
            }}>
              {group}
            </div>
            {items.map(item => (
              <button key={item.id} onClick={() => handleClick(item)}
                className="w-full text-left rounded-xl transition-all duration-150"
                style={{
                  padding: '10px 12px', marginBottom: 2,
                  background:  activeConv === item.id ? 'rgba(255,121,0,0.08)' : 'transparent',
                  borderLeft:  activeConv === item.id ? '2px solid #FF7900'    : '2px solid transparent',
                  cursor: 'pointer',
                }}>
                <div style={{
                  fontSize: 12.5, fontWeight: 400, color: 'rgba(255,255,255,0.78)',
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {buildTitle(item)}
                </div>
                <div className="flex items-center gap-1.5" style={{ marginTop: 6 }}>
                  <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.28)' }}>
                    {formatTime(item.created_at)}
                  </span>
                  <Tag label="PPT" color="orange" />
                  {item.a_fibre     && <Tag label="Fibre" color="teal"   />}
                  {item.a_microsoft && <Tag label="MS365" color="purple" />}
                </div>
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2"
        style={{ padding: '12px 20px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <span className="pulse-dot rounded-full"
          style={{ width: 8, height: 8, background: '#22C55E', flexShrink: 0 }} />
        <span style={{ fontSize: 11, fontWeight: 300, color: 'rgba(255,255,255,0.32)', letterSpacing: '0.01em' }}>
          4 agents actifs · LLaMA 3.3 70B
        </span>
      </div>
    </div>
  )
}
