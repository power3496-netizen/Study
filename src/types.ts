export type ExamType = 'electric_engineer' | 'electric_construction'
export type Filter = 'all' | 'unlearned' | 'starred' | 'difficult' | 'mastered'
export type Question = {
  id: number; year: number; question: string; answer: string; explanation: string; exam_type: ExamType
  starred: boolean; mastered: boolean; wrong_count: number; last_answer: string
}
export type YearSummary = { year: number; total: number; mastered: number; starred: number; difficult: number }
export type Stats = { total: number; mastered: number; starred: number; wrongs: number; recent: Array<{ id: number; question: string; year: number; result: string; created_at: string }> }
export type ExamSettings = { selected_round: 1 | 2 | 3 | null; round_1_date: string; round_2_date: string; round_3_date: string }

export type PassRate = { id: number; year: number; round: 1 | 2 | 3; applicants: number; passers: number; rate: number }
