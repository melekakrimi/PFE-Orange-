import AgentSteps from './AgentSteps'
import ResultCard  from './ResultCard'

const OrangeAvatar = () => (
  <div className="flex items-center justify-center rounded-xl"
    style={{ width: 34, height: 34, background: 'linear-gradient(135deg,#FF7900,#FF4500)', flexShrink: 0 }}>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9"   stroke="white" strokeWidth="2.2" />
      <circle cx="12" cy="12" r="4.5" fill="white" />
    </svg>
  </div>
)

const UserAvatar = () => (
  <div className="flex items-center justify-center rounded-xl"
    style={{ width: 34, height: 34, background: 'rgba(255,255,255,0.07)',
      border: '1px solid rgba(255,255,255,0.10)', flexShrink: 0,
      fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.45)' }}>
    MK
  </div>
)

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`anim-fadeUp flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
      style={{ alignItems: 'flex-start' }}>

      {/* Avatar */}
      <div style={{ marginTop: 2 }}>
        {isUser ? <UserAvatar /> : <OrangeAvatar />}
      </div>

      {/* Content */}
      <div style={{ display: 'flex', flexDirection: 'column', maxWidth: '72%',
        alignItems: isUser ? 'flex-end' : 'flex-start' }}>

        {/* Agent steps — only on AI messages */}
        {!isUser && message.agentTimes && (
          <AgentSteps agents={message.agentTimes} />
        )}

        {/* Bubble */}
        <div style={isUser ? {
          background: 'linear-gradient(135deg,#FF7900,#FF5200)',
          borderRadius: '16px 4px 16px 16px',
          padding: '11px 16px',
          fontSize: 13.5, fontWeight: 400, lineHeight: 1.6,
          color: 'white', letterSpacing: '-0.01em',
        } : {
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRadius: '4px 16px 16px 16px',
          padding: '11px 16px',
          fontSize: 13.5, fontWeight: 400, lineHeight: 1.65,
          color: 'rgba(255,255,255,0.82)', letterSpacing: '-0.005em',
        }}>
          {message.content}
        </div>

        {/* Result card — only on AI messages */}
        {!isUser && message.result && (
          <ResultCard result={message.result} />
        )}
      </div>
    </div>
  )
}
