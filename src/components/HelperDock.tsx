import { useEffect, useState } from 'react'
import { api } from '../lib/api'
type Chat = { id: number; role: 'user' | 'assistant'; text: string }
export function HelperDock() {
  const [open, setOpen] = useState(true)
  const [text, setText] = useState('')
  const [chats, setChats] = useState<Chat[]>([])
  const [sending, setSending] = useState(false)
  const [notice, setNotice] = useState('')
  useEffect(() => {
    if (!open || chats.length) return
    api('helper').then(async (response) => {
      if (!response.ok) throw new Error()
      setChats(await response.json())
    }).catch(() => setNotice('대화 내용을 불러오지 못했어요.'))
  }, [open, chats.length])
  const send = async () => {
    const question = text.trim()
    if (!question || sending) return
    setText(''); setSending(true); setNotice('')
    try {
      const response = await api('helper', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '답변을 가져오지 못했어요.')
      setChats((items) => [...items, data.user, data.assistant])
    } catch (error) { setNotice(error instanceof Error ? error.message : '잠시 후 다시 질문해 주세요.') }
    finally { setSending(false) }
  }
  return <aside className={`helper ${open ? 'is-open' : ''}`} aria-label="AI 학습 도우미">
    <button className="helper-toggle press" onClick={() => setOpen(!open)} aria-expanded={open}>✦ AI 학습 도우미</button>
    {open && <div className="helper-panel">
      <strong>챗GPT에게 개념 질문하기</strong><p>전기 관련 개념과 해설을 한국어로 간단히 물어보세요.</p>
      <div className="chat-log" aria-live="polite">{chats.length === 0 ? <span>예: 접지저항 저감 방법을 간단히 설명해 줘</span> : chats.map((chat) => <div className={`chat ${chat.role}`} key={chat.id}>{chat.text}</div>)}{sending && <div className="chat assistant">답변을 작성하고 있어요.</div>}</div>
      {notice && <p className="form-error" role="alert">{notice}</p>}
      <div className="chat-input"><input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder="궁금한 내용을 입력하세요" aria-label="학습 질문" /><button className="press" onClick={send} disabled={sending}>{sending ? '답변 중' : '묻기'}</button></div>
    </div>}
  </aside>
}
