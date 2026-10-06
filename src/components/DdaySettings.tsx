import { PassRateManager } from './PassRateManager'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { ExamSettings, ExamType, PassRate } from '../types'
const emptySettings: ExamSettings = { selected_round: null, round_1_date: '', round_2_date: '', round_3_date: '' }
export function DdaySettings({ examType, settings, rates, isAdmin, onClose, onSaved, onRatesChanged }: { examType: ExamType; settings: ExamSettings; rates: PassRate[]; isAdmin: boolean; onClose: () => void; onSaved: (settings: ExamSettings) => void; onRatesChanged: () => void }) {
  const [form, setForm] = useState<ExamSettings>(settings || emptySettings)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { setForm(settings || emptySettings); setError('') }, [settings, examType])
  const save = async () => {
    if (form.selected_round && !form[`round_${form.selected_round}_date` as keyof ExamSettings]) { setError('선택한 회차의 시험 날짜를 입력해 주세요.'); return }
    setBusy(true); setError('')
    try {
      const response = await api(`exam-settings?exam_type=${examType}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '저장하지 못했어요.')
      onSaved(data)
      onClose()
    } catch (err) { setError(err instanceof Error ? err.message : '저장하지 못했어요.') }
    finally { setBusy(false) }
  }
  return <div className="modal-backdrop" role="presentation"><section className="editor-modal settings-modal" role="dialog" aria-modal="true" aria-label="디데이 관리"><div className="modal-head"><div><span className="eyebrow">EXAM COUNTDOWN</span><h2>디데이 관리</h2></div><button className="icon-button" onClick={onClose} aria-label="닫기">×</button></div><p className="settings-intro">회차별 시험 날짜를 입력하고, 메인 화면에 표시할 회차를 하나 선택하세요.</p><div className="round-form">{([1, 2, 3] as const).map((round) => <label className={`round-row ${form.selected_round === round ? 'is-selected' : ''}`} key={round}><span><input type="radio" name="selected-round" checked={form.selected_round === round} onChange={() => setForm({ ...form, selected_round: round })} /> {round}회차</span><input type="date" value={form[`round_${round}_date`]} onChange={(event) => setForm({ ...form, [`round_${round}_date`]: event.target.value })} aria-label={`${round}회차 시험 날짜`} /></label>)}</div><button className="clear-round" onClick={() => setForm({ ...form, selected_round: null })}>선택 회차 해제</button>{isAdmin ? <PassRateManager examType={examType} rates={rates} onChanged={onRatesChanged} /> : <section className="shared-rate-note" aria-label="공통 합격률 안내"><b>공통 최근 합격률</b><p>최근 합격률은 모든 학습 번호에 동일하게 표시됩니다. 변경은 관리자 모드에서 할 수 있어요.</p></section>}{error && <p className="form-error" role="alert">{error}</p>}<div className="modal-actions"><span /><button className="secondary press" onClick={onClose}>취소</button><button className="primary press" onClick={save} disabled={busy}>{busy ? '저장 중' : '저장하기'}</button></div></section></div>
}
