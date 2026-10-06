import { useState } from 'react'
import { api } from '../lib/api'
type AuthProps = { onSuccess: (pin: string) => void }
export function LoginGate({ onSuccess }: AuthProps) {
  const [pin, setPin] = useState('')
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (admin = false) => {
    const enteredPin = admin ? '0000' : pin
    if (!admin && !/^\d{4}$/.test(enteredPin)) { setNotice('숫자 네 자리를 입력해 주세요.'); return }
    setBusy(true); setNotice('')
    try {
      const response = await api('auth', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin: enteredPin, action: 'login' }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '처리하지 못했어요.')
      onSuccess(data.pin)
    } catch (error) { setNotice(error instanceof Error ? error.message : '잠시 후 다시 시도해 주세요.') }
    finally { setBusy(false) }
  }
  const signup = async () => {
    if (!/^\d{4}$/.test(pin)) { setNotice('숫자 네 자리를 입력해 주세요.'); return }
    setBusy(true); setNotice('')
    try {
      const response = await api('auth', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin, action: 'signup' }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '처리하지 못했어요.')
      onSuccess(data.pin)
    } catch (error) { setNotice(error instanceof Error ? error.message : '잠시 후 다시 시도해 주세요.') }
    finally { setBusy(false) }
  }
  return <main className="login-page"><section className="login-card" aria-labelledby="login-title"><span className="sticker">나만의 학습 기록</span><h1 id="login-title"><span>⚡</span> 전기기사<br /><em>단답 마스터</em></h1><p>공통 문제를 학습하고, 나의 답안·별표·암기 완료·오답 기록은 번호별로 따로 저장하세요.</p><div className="auth-tabs" role="tablist"><button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setNotice('') }} role="tab">로그인</button><button className={mode === 'signup' ? 'active' : ''} onClick={() => { setMode('signup'); setNotice('') }} role="tab">새로 가입</button></div><label htmlFor="study-pin">네 자리 번호<input id="study-pin" inputMode="numeric" autoComplete="off" maxLength={4} value={pin} onChange={(event) => setPin(event.target.value.replace(/\D/g, '').slice(0, 4))} onKeyDown={(event) => event.key === 'Enter' && (mode === 'login' ? submit() : signup())} placeholder="예: 1234" aria-describedby="pin-guide" /></label><small id="pin-guide">같은 번호로 로그인하면 이전 학습 기록을 다시 불러옵니다.</small>{notice && <p className="form-error" role="alert">{notice}</p>}<button className="primary press auth-submit" onClick={() => mode === 'login' ? submit() : signup()} disabled={busy}>{busy ? '확인 중' : mode === 'login' ? '로그인하기 →' : '가입하고 시작하기 →'}</button><div className="admin-entry"><span>문제 목록을 관리하시나요?</span><button className="secondary press" onClick={() => submit(true)} disabled={busy}>관리자 모드</button></div></section></main>
}
