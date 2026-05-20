import { useState } from 'react'

const LS_KEY = 'ob_history'

function loadFromStorage() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || '[]')
  } catch {
    return []
  }
}

function saveToStorage(history) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(history.slice(0, 50)))
  } catch {}
}

export default function useChat() {
  const [messages,     setMessages]     = useState([])
  const [isTyping,     setIsTyping]     = useState(false)
  const [activeClient, setActiveClient] = useState(null)
  const [localHistory, setLocalHistory] = useState(loadFromStorage)  // persist localStorage

  const loadProposition = (data) => {
    if (!data) {
      setMessages([])
      setActiveClient(null)
      return
    }
    setActiveClient({ name: data.client, secteur: data.secteur })
    setMessages([{
      role:       'ai',
      id:         `loaded-${data.id || Date.now()}`,
      content:    data.pitch_commercial || `Proposition commerciale Orange Business pour ${data.client}.`,
      agentTimes: data.agent_times || null,
      result:     data,
    }])
  }

  const sendMessage = async (text) => {
    setMessages(prev => [...prev, {
      role: 'user',
      id:   Date.now(),
      content: text,
    }])
    setIsTyping(true)

    try {
      const res = await fetch('/generate', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ description: text }),
      })

      if (res.status === 502 || res.status === 503) {
        throw new Error("Le backend FastAPI n'est pas lancé — exécutez : python api.py")
      }

      let data
      try { data = await res.json() }
      catch { throw new Error("Le backend FastAPI n'est pas lancé — exécutez : python api.py") }

      if (!res.ok) throw new Error(data.detail || `Erreur serveur ${res.status}`)

      setIsTyping(false)
      setActiveClient({ name: data.client, secteur: data.secteur })

      // Ajoute à l'historique local (session en mémoire)
      const sessionEntry = {
        id:             `local-${Date.now()}`,
        entreprise:     data.client,
        secteur:        data.secteur,
        created_at:     new Date().toISOString(),
        a_fibre:        !!data.fibre,
        a_microsoft:    !!data.microsoft,
        plan_recommande: data.microsoft?.nom_produit || data.fibre?.nom_offre || '',
        result:         data,
      }
      setLocalHistory(prev => {
        const updated = [sessionEntry, ...prev]
        saveToStorage(updated)
        return updated
      })

      setMessages(prev => [...prev, {
        role:       'ai',
        id:         Date.now() + 1,
        content:    data.pitch_commercial,
        agentTimes: data.agent_times,
        result:     data,
      }])

      // Rafraîchit aussi la sidebar depuis la DB (si connectée)
      window.dispatchEvent(new Event('refresh-history'))

    } catch (err) {
      setIsTyping(false)
      setMessages(prev => [...prev, {
        role: 'ai', id: Date.now() + 1,
        content: `⚠ ${err.message}`,
        agentTimes: null, result: null,
      }])
    }
  }

  return { messages, isTyping, activeClient, localHistory, sendMessage, loadProposition }
}
