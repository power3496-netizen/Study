import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Question } from '../types'
type Verdict = 'correct' | 'wrong' | null
type StudyMode = 'test' | 'practice'
export function StudyView({ title, questions, initialIndex, mode = 'test', onBack, onRefresh, onPatch }: { title:string; questions:Question[]; initialIndex:number; mode?: StudyMode; onBack:()=>void; onRefresh:()=>void; onPatch:(id:number, path:'starred'|'mastered', value:boolean)=>Promise<void> }) {
 const [index,setIndex]=useState(initialIndex); const [answer,setAnswer]=useState(''); const [revealed,setRevealed]=useState(mode === 'practice'); const [verdict,setVerdict]=useState<Verdict>(null); const [saved,setSaved]=useState(false)
 const q=questions[index]
 useEffect(()=>{setAnswer(q?.last_answer||'');setRevealed(mode === 'practice');setVerdict(null);setSaved(false)},[index,q?.id,mode])
 if(!q) return <div className="empty"><b>학습할 문제가 없어요.</b><button className="secondary press" onClick={onBack}>목록으로 돌아가기</button></div>
 const save=async(result:'correct'|'wrong')=>{ if(saved)return; try{const response=await api(`questions/${q.id}/review`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answer_text:answer,result})});if(!response.ok)throw new Error();setVerdict(result);setSaved(true);onRefresh()}catch{alert('기록 저장에 실패했어요.')} }
 const move=(way:number)=>setIndex((old)=>Math.min(Math.max(0,old+way),questions.length-1))
 const practice = mode === 'practice'
 return <section className="study-page"><div className="study-top"><button className="back-link" onClick={onBack}>← 목록</button><span className="study-count tabular">{index+1} / {questions.length}</span><button className="icon-button press" onClick={()=>onPatch(q.id,'starred',!q.starred)}>{q.starred?'★':'☆'}</button></div><div className="progress"><i style={{width:`${((index+1)/questions.length)*100}%`}} /></div>
 <article className="study-card"><span className="eyebrow">{title} · {practice ? '답안 함께 보기' : '단답형'}</span><p className="study-question">{q.question}</p>
 {practice ? <section className="practice-answer-panel" aria-label="정답"><div className="practice-answer-head"><span>정답</span><b>바로 확인</b></div><p className="practice-answer">{q.answer || '등록된 정답이 없어요.'}</p><p className="practice-note">답안을 보며 핵심 표현을 익히는 연습 모드입니다. 채점 기록은 남기지 않아요.</p></section> : <><label htmlFor="answer">나의 답안</label><textarea id="answer" value={answer} onChange={e=>setAnswer(e.target.value)} disabled={revealed} placeholder="기억나는 답을 직접 입력해 보세요." />
 {!revealed ? <button className="primary large press" onClick={()=>setRevealed(true)} disabled={!answer.trim()}>정답 확인하기</button> : <div className="reveal"><div className="answer-compare"><div><span>나의 답안</span><p>{answer||'입력한 답안이 없어요.'}</p></div><div className="official"><span>모범 답안</span><p>{q.answer}</p></div></div><div className="verdict"><strong>채점 결과를 직접 확인해 주세요.</strong><p>{q.wrong_count > 0 ? `누적 오답 ${q.wrong_count}회 · 이번 결과를 기록하면 복습 우선순위에 반영됩니다.` : '첫 풀이 기록을 남겨 보세요.'}</p><div><button className={`verdict-button correct press ${verdict==='correct'?'selected':''}`} onClick={()=>save('correct')} disabled={saved}>✓ 정답이에요</button><button className={`verdict-button wrong press ${verdict==='wrong'?'selected':''}`} onClick={()=>save('wrong')} disabled={saved}>✕ 다시 볼래요</button></div>{saved&&<small>학습 기록을 저장했어요.</small>}</div></div>}</>}</article>
 <div className="study-nav"><button className="secondary press" onClick={()=>move(-1)} disabled={index===0}>← 이전 문제</button><button className="secondary press" onClick={()=>onPatch(q.id,'mastered',!q.mastered)}>{q.mastered?'암기 완료 취소':'✓ 암기 완료'}</button><button className="primary press" onClick={()=>move(1)} disabled={index===questions.length-1}>다음 문제 →</button></div></section>
}
