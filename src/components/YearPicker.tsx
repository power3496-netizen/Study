import { PassRateStrip } from './PassRateStrip'
import type { ExamSettings, ExamType, PassRate, YearSummary } from '../types'
const examName: Record<ExamType, string> = { electric_engineer: '전기기사', electric_construction: '전기공사기사' }
function countdown(settings: ExamSettings) {
  const round = settings.selected_round
  const date = round ? settings[`round_${round}_date`] : ''
  if (!round) return '회차를 선택하세요'
  if (!date) return `${round}회차 · 날짜 미입력`
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const target = new Date(`${date}T00:00:00`)
  const days = Math.round((target.getTime() - today.getTime()) / 86400000)
  return `${round}회차 ${days >= 0 ? `D-${String(days).padStart(2, '0')}일` : `D+${String(Math.abs(days)).padStart(2, '0')}일`}`
}
export function YearPicker({ years, examType, settings, rates, onChoose }: { years: YearSummary[]; examType: ExamType; settings: ExamSettings; rates: PassRate[]; onChoose: (year: number) => void }) {
  const name = examName[examType]
  const dday = countdown(settings)
  return <section className="year-page">
    <div className="hero"><div className="hero-stickers"><span className="sticker">2012 — 2026</span><span className="dday-badge" aria-label={`선택한 시험 ${dday}`}>시험 {dday}</span></div><h1>{name}<br /><em>단답 마스터</em></h1><p>{name} 단답 문제를 정리하고, 답안을 직접 쓰고, 약한 부분만 다시 복습하세요.</p></div>
    <PassRateStrip rates={rates} />
    <div className="year-grid">{years.map((item) => <button className="year-card press" key={item.year} onClick={() => onChoose(item.year)}>
      <span className="year-number">{item.year}</span><span className="year-label">년 기출 단답</span>
      <div className="year-stats"><b>전체 {item.total}</b><span>완료 {item.mastered}</span><span>★ {item.starred}</span><span>오답많음 {item.difficult}</span></div>
    </button>)}</div>
  </section>
}
