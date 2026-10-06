import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import type { ExamType, PassRate } from '../types'
export function PassRateManager({ examType, rates, onChanged }: { examType: ExamType; rates: PassRate[]; onChanged: () => void }) {
  const [year, setYear] = useState('2026')
  const [round, setRound] = useState('1')
  const [applicants, setApplicants] = useState('')
  const [passers, setPassers] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const selected = useMemo(() => rates.find((item) => item.year === Number(year) && item.round === Number(round)), [rates, year, round])
  const save = async () => {
    const applied = Number(applicants)
    const passed = Number(passers)
    if (!Number.isInteger(applied) || !Number.isInteger(passed) || applied < 0 || passed < 0) { setError('응시인원과 합격인원은 0명 이상의 정수로 입력해 주세요.'); return }
    if (passed > applied) { setError('합격인원은 응시인원보다 많을 수 없어요.'); return }
    setBusy(true); setError('')
    try {
      const response = await api(`pass-rates?exam_type=${examType}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ year: Number(year), round: Number(round), applicants: applied, passers: passed }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '저장하지 못했어요.')
      setApplicants(''); setPassers(''); onChanged()
    } catch (err) { setError(err instanceof Error ? err.message : '저장하지 못했어요.') } finally { setBusy(false) }
  }
  const remove = async () => {
    if (!selected || !confirm(`${selected.year}년 ${selected.round}회차 합격률을 삭제할까요?`)) return
    try { const response = await api(`pass-rates/${selected.id}?exam_type=${examType}`, { method: 'DELETE' }); if (!response.ok) throw new Error(); onChanged() } catch { setError('삭제하지 못했어요.') }
  }
  return <section className="pass-rate-manager" aria-labelledby="pass-rate-title">
    <div className="pass-rate-title"><div><span className="eyebrow">PASS RATE</span><h3 id="pass-rate-title">합격률 관리</h3></div><strong>{selected ? `${selected.rate}%` : '새 기록'}</strong></div>
    <p>합격률은 <b>합격인원 ÷ 응시인원 × 100</b>으로 계산됩니다.</p>
    <div className="pass-rate-form"><label>연도<select value={year} onChange={(event) => setYear(event.target.value)}>{Array.from({ length: 15 }, (_, index) => 2026 - index).map((item) => <option value={item} key={item}>{item}년</option>)}</select></label><label>회차<select value={round} onChange={(event) => setRound(event.target.value)}>{[1, 2, 3].map((item) => <option value={item} key={item}>{item}회차</option>)}</select></label><label>응시인원<input type="number" min="0" value={applicants} onChange={(event) => setApplicants(event.target.value)} placeholder={selected ? String(selected.applicants) : '예: 1000'} /></label><label>합격인원<input type="number" min="0" value={passers} onChange={(event) => setPassers(event.target.value)} placeholder={selected ? String(selected.passers) : '예: 250'} /></label></div>
    {selected && <p className="saved-rate">저장됨 · 응시 {selected.applicants.toLocaleString()}명 / 합격 {selected.passers.toLocaleString()}명</p>}{error && <p className="form-error" role="alert">{error}</p>}
    <div className="pass-rate-actions"><button className="secondary press" onClick={remove} disabled={!selected}>선택 기록 삭제</button><button className="primary press" onClick={save} disabled={busy}>{busy ? '저장 중' : '합격률 저장'}</button></div>
  </section>
}
