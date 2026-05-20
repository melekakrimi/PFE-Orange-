const CheckIcon = () => (
  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
    <path d="M1.5 5l2.5 2.5 4.5-4" stroke="#14B8A6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

export default function AgentSteps({ agents }) {
  return (
    <div className="flex flex-wrap gap-2" style={{ marginBottom: 10 }}>
      {agents.map((a, i) => (
        <div
          key={a.label}
          className="anim-popIn flex items-center gap-1.5 rounded-full"
          style={{
            animationDelay: `${i * 0.18}s`,
            padding: '5px 11px',
            background: 'rgba(20,184,166,0.08)',
            border: '1px solid rgba(20,184,166,0.22)',
            fontSize: 11,
          }}>
          <CheckIcon />
          <span style={{ color: 'rgba(255,255,255,0.50)', fontWeight: 400 }}>{a.label}</span>
          <span style={{ color: 'rgba(255,255,255,0.18)' }}>·</span>
          <span style={{ color: '#14B8A6', fontWeight: 500 }}>{a.name}</span>
          <span style={{ color: 'rgba(255,255,255,0.18)' }}>·</span>
          <span style={{ color: 'rgba(255,255,255,0.35)', fontWeight: 300 }}>{a.time}</span>
        </div>
      ))}
    </div>
  )
}