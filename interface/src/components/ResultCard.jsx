const IconChart = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M2 13L5.5 7.5l3 3.5 2.5-5L14 9" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)
const IconFibre = () => (
  <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
    <path d="M7 1C3.5 1 1 4 1 7s2.5 6 6 6" stroke="#14B8A6" strokeWidth="1.4" strokeLinecap="round" />
    <path d="M7 4C5.3 4 4 5.3 4 7s1.3 3 3 3" stroke="#14B8A6" strokeWidth="1.4" strokeLinecap="round" />
    <circle cx="7" cy="7" r="1.2" fill="#14B8A6" />
  </svg>
)
const IconMS = () => (
  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
    <rect x="1"   y="1"   width="5" height="5" rx="0.8" fill="#A78BFA" opacity="0.85" />
    <rect x="7"   y="1"   width="5" height="5" rx="0.8" fill="#A78BFA" opacity="0.65" />
    <rect x="1"   y="7"   width="5" height="5" rx="0.8" fill="#A78BFA" opacity="0.65" />
    <rect x="7"   y="7"   width="5" height="5" rx="0.8" fill="#A78BFA" opacity="0.45" />
  </svg>
)
const IconDoc = () => (
  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
    <rect x="2" y="1" width="9" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
    <path d="M4 4.5h5M4 6.5h5M4 8.5h3" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
  </svg>
)

export default function ResultCard({ result }) {
  const r = result || {}
  const dateStr = new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })

  const handleDownload = (path) => {
    if (path) window.open(`/download/${path}`, '_blank')
  }

  return (
    <div className="anim-slideUp glass-card rounded-2xl overflow-hidden"
      style={{ animationDelay: '0.55s', marginTop: 12, width: '100%' }}>

      {/* ── Header ── */}
      <div className="flex items-center justify-between"
        style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center rounded-xl"
            style={{ width: 38, height: 38, background: 'linear-gradient(135deg,#FF7900,#FF4500)', flexShrink: 0 }}>
            <IconChart />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#F8F8F8', letterSpacing: '-0.02em' }}>
              Proposition — {r.client || 'Client'}
            </div>
            <div style={{ fontSize: 11, fontWeight: 300, color: 'rgba(255,255,255,0.32)', marginTop: 2 }}>
              {dateStr} · Validité 30 jours
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 rounded-full"
          style={{
            padding: '5px 12px',
            background: 'rgba(34,197,94,0.10)',
            border: '1px solid rgba(34,197,94,0.25)',
            fontSize: 11, fontWeight: 600, color: '#22C55E',
          }}>
          Marge OK ✓
        </div>
      </div>

      {/* ── KPI grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, padding: '16px 20px 12px' }}>
        {[
          { label: 'Prix annuel',  value: `${(r.prix_annuel  || 0).toLocaleString('fr-FR')} TND`, green: false },
          { label: 'Mensuel',      value: `${(r.prix_mensuel || 0).toLocaleString('fr-FR')} TND`, green: false },
          { label: 'Taux marge',   value: `${r.taux_marge || 0}%`,                                green: true  },
        ].map(kpi => (
          <div key={kpi.label} className="kpi-card rounded-xl" style={{ padding: '14px 16px', background: 'rgba(255,255,255,0.03)', cursor: 'default' }}>
            <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.32)',
              textTransform: 'uppercase', letterSpacing: '0.09em', marginBottom: 8 }}>
              {kpi.label}
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em',
              color: kpi.green ? '#22C55E' : '#F8F8F8' }}>
              {kpi.value}
            </div>
          </div>
        ))}
      </div>

      {/* ── Solution tags ── */}
      <div className="flex flex-wrap gap-2" style={{ padding: '0 20px 14px' }}>
        {r.fibre && (
          <div className="flex items-center gap-1.5 rounded-xl"
            style={{ padding: '7px 12px', background: 'rgba(20,184,166,0.08)', border: '1px solid rgba(20,184,166,0.20)',
              fontSize: 12, fontWeight: 500, color: '#14B8A6' }}>
            <IconFibre />
            {r.fibre.nom_offre} · {r.fibre.debit_mbps} Mbps · {r.fibre.engagement_mois} mois
          </div>
        )}
        {r.microsoft && (
          <div className="flex items-center gap-1.5 rounded-xl"
            style={{ padding: '7px 12px', background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.20)',
              fontSize: 12, fontWeight: 500, color: '#A78BFA' }}>
            <IconMS />
            {r.microsoft.nom_produit} · {r.microsoft.nombre_licences} licences
          </div>
        )}
      </div>

      {/* ── Download buttons ── */}
      <div className="flex gap-2" style={{ padding: '0 20px 18px' }}>
        <button
          className="flex items-center gap-2 rounded-xl glow-btn"
          style={{
            padding: '9px 20px',
            background: 'linear-gradient(135deg,#FF7900,#FF4500)',
            border: 'none', cursor: 'pointer',
            fontSize: 13, fontWeight: 600, color: 'white',
          }}
          onClick={() => handleDownload(r.pptx_path)}>
          <IconDoc />
          PowerPoint
        </button>
        {[
          { label: 'Word', path: r.word_path },
          { label: 'PDF',  path: r.pdf_path  },
        ].map(btn => (
          <button key={btn.label}
            className="flex items-center gap-1.5 rounded-xl transition-all duration-150 hover:bg-white/10"
            style={{
              padding: '9px 16px',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.09)',
              cursor: 'pointer',
              fontSize: 13, fontWeight: 500, color: 'rgba(255,255,255,0.50)',
            }}
            onClick={() => handleDownload(btn.path)}>
            <IconDoc />
            {btn.label}
          </button>
        ))}

        {r.temps_generation && (
          <div className="flex items-center ml-auto"
            style={{ fontSize: 11, fontWeight: 300, color: 'rgba(255,255,255,0.22)' }}>
            Généré en {r.temps_generation}s
          </div>
        )}
      </div>
    </div>
  )
}
