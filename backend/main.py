import json
import os
import sqlite3
import urllib.error
import urllib.request
from contextvars import ContextVar
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
DB_PATH = "data/app.db"
YEARS = list(range(2012, 2027))
EXAMS = {"electric_engineer", "electric_construction"}
ADMIN_PIN = "0000"
current_user_pin: ContextVar[Optional[str]] = ContextVar("current_user_pin", default=None)
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    with get_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            pin TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER NOT NULL,
            question TEXT NOT NULL, answer TEXT NOT NULL,
            explanation TEXT NOT NULL DEFAULT '', starred INTEGER NOT NULL DEFAULT 0,
            mastered INTEGER NOT NULL DEFAULT 0, wrong_count INTEGER NOT NULL DEFAULT 0,
            last_answer TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        question_columns = {row["name"] for row in conn.execute("PRAGMA table_info(questions)").fetchall()}
        if "exam_type" not in question_columns:
            conn.execute("ALTER TABLE questions ADD COLUMN exam_type TEXT NOT NULL DEFAULT 'electric_engineer'")
        if "user_pin" not in question_columns:
            conn.execute("ALTER TABLE questions ADD COLUMN user_pin TEXT NOT NULL DEFAULT '0000'")
        conn.execute("""CREATE TABLE IF NOT EXISTS learning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, question_id INTEGER NOT NULL,
            answer_text TEXT NOT NULL DEFAULT '', result TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        record_columns = {row["name"] for row in conn.execute("PRAGMA table_info(learning_records)").fetchall()}
        if "user_pin" not in record_columns:
            conn.execute("ALTER TABLE learning_records ADD COLUMN user_pin TEXT NOT NULL DEFAULT '0000'")
            conn.execute("""UPDATE learning_records SET user_pin=COALESCE(
                (SELECT user_pin FROM questions WHERE questions.id=learning_records.question_id), '0000')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS common_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER NOT NULL,
            question TEXT NOT NULL, answer TEXT NOT NULL,
            explanation TEXT NOT NULL DEFAULT '', exam_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS question_progress (
            user_pin TEXT NOT NULL, question_id INTEGER NOT NULL,
            starred INTEGER NOT NULL DEFAULT 0, mastered INTEGER NOT NULL DEFAULT 0,
            wrong_count INTEGER NOT NULL DEFAULT 0, last_answer TEXT NOT NULL DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_pin, question_id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        )""")
        migrated = conn.execute("SELECT 1 FROM app_meta WHERE key='common_questions_migrated'").fetchone()
        if not migrated:
            conn.execute("""INSERT OR IGNORE INTO common_questions
                (id, year, question, answer, explanation, exam_type, created_at, updated_at)
                SELECT id, year, question, answer, explanation, exam_type, created_at, updated_at FROM questions""")
            conn.execute("""INSERT OR IGNORE INTO question_progress
                (user_pin, question_id, starred, mastered, wrong_count, last_answer, updated_at)
                SELECT user_pin, id, starred, mastered, wrong_count, last_answer, updated_at FROM questions""")
            conn.execute("INSERT INTO app_meta(key, value) VALUES ('common_questions_migrated', ?)", (datetime.now().isoformat(timespec="seconds"),))
        conn.execute("""CREATE TABLE IF NOT EXISTS helper_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            text TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        helper_columns = {row["name"] for row in conn.execute("PRAGMA table_info(helper_messages)").fetchall()}
        if "user_pin" not in helper_columns:
            conn.execute("ALTER TABLE helper_messages ADD COLUMN user_pin TEXT NOT NULL DEFAULT '0000'")
        conn.execute("""CREATE TABLE IF NOT EXISTS exam_settings_users (
            user_pin TEXT NOT NULL, exam_type TEXT NOT NULL, selected_round INTEGER,
            round_1_date TEXT NOT NULL DEFAULT '', round_2_date TEXT NOT NULL DEFAULT '',
            round_3_date TEXT NOT NULL DEFAULT '', updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_pin, exam_type)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pass_rates_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_pin TEXT NOT NULL, exam_type TEXT NOT NULL,
            year INTEGER NOT NULL, round INTEGER NOT NULL, applicants INTEGER NOT NULL DEFAULT 0,
            passers INTEGER NOT NULL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_pin, exam_type, year, round)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pass_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT, exam_type TEXT NOT NULL,
            year INTEGER NOT NULL, round INTEGER NOT NULL, applicants INTEGER NOT NULL DEFAULT 0,
            passers INTEGER NOT NULL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(exam_type, year, round)
        )""")
        shared_rates_migrated = conn.execute("SELECT 1 FROM app_meta WHERE key='shared_pass_rates_migrated'").fetchone()
        if not shared_rates_migrated:
            conn.execute("""INSERT OR IGNORE INTO pass_rates(exam_type, year, round, applicants, passers, updated_at)
                SELECT exam_type, year, round, applicants, passers, updated_at FROM pass_rates_users
                ORDER BY CASE WHEN user_pin=? THEN 0 ELSE 1 END, updated_at DESC""", (ADMIN_PIN,))
            conn.execute("INSERT INTO app_meta(key, value) VALUES ('shared_pass_rates_migrated', ?)", (datetime.now().isoformat(timespec="seconds"),))
        conn.execute("INSERT OR IGNORE INTO users(pin) VALUES (?)", (ADMIN_PIN,))
        conn.execute("CREATE INDEX IF NOT EXISTS idx_common_questions_exam_year ON common_questions(exam_type, year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_progress_user_question ON question_progress(user_pin, question_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_user_question ON learning_records(user_pin, question_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_helper_user ON helper_messages(user_pin, id)")
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 주소(Vercel 웹사이트 등)에서의 요청을 허용합니다
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST 등 모든 통신 방법을 허용합니다
    allow_headers=["*"],  # 모든 헤더 정보를 허용합니다
)
init_db()
class AuthInput(BaseModel):
    pin: str
    action: str
class QuestionInput(BaseModel):
    year: int
    question: str
    answer: str
    explanation: Optional[str] = None
    exam_type: str
class ReviewInput(BaseModel):
    answer_text: str = ''
    result: str
class FlagInput(BaseModel):
    value: bool
class ExamSettingsInput(BaseModel):
    selected_round: Optional[int] = None
    round_1_date: str = ''
    round_2_date: str = ''
    round_3_date: str = ''
class PassRateInput(BaseModel):
    year: int
    round: int
    applicants: int
    passers: int
@app.middleware("http")
async def require_user(request: Request, call_next):
    if request.url.path in ("/api/health", "/api/auth"):
        return await call_next(request)
    pin = request.headers.get("X-Study-User", "")
    if not (len(pin) == 4 and pin.isdigit()):
        return JSONResponse(status_code=401, content={"detail": "네 자리 번호로 로그인해 주세요."})
    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE pin=?", (pin,)).fetchone()
    if not exists:
        return JSONResponse(status_code=401, content={"detail": "등록되지 않은 번호예요."})
    token = current_user_pin.set(pin)
    try:
        return await call_next(request)
    finally:
        current_user_pin.reset(token)
def user_pin():
    pin = current_user_pin.get()
    if not pin:
        raise HTTPException(401, "로그인이 필요해요.")
    return pin
def require_admin():
    if user_pin() != ADMIN_PIN:
        raise HTTPException(403, "관리자 모드에서만 문제를 관리할 수 있어요.")
def validate_exam(exam_type: str):
    if exam_type not in EXAMS:
        raise HTTPException(400, "시험 종류를 확인해 주세요.")
def question_dict(row):
    return {"id": row["id"], "year": row["year"], "question": row["question"], "answer": row["answer"],
            "explanation": row["explanation"], "exam_type": row["exam_type"], "starred": bool(row["starred"]),
            "mastered": bool(row["mastered"]), "wrong_count": int(row["wrong_count"]), "last_answer": row["last_answer"]}
def question_select():
    return """SELECT cq.*, COALESCE(qp.starred, 0) starred, COALESCE(qp.mastered, 0) mastered,
        COALESCE(qp.wrong_count, 0) wrong_count, COALESCE(qp.last_answer, '') last_answer
        FROM common_questions cq LEFT JOIN question_progress qp
        ON qp.question_id=cq.id AND qp.user_pin=?"""
def get_question(conn, question_id: int, pin: str):
    return conn.execute(question_select() + " WHERE cq.id=?", (pin, question_id)).fetchone()
def setting_dict(row):
    return {"selected_round": row["selected_round"], "round_1_date": row["round_1_date"], "round_2_date": row["round_2_date"], "round_3_date": row["round_3_date"]}
def pass_rate_dict(row):
    applicants, passers = int(row["applicants"]), int(row["passers"])
    return {"id": row["id"], "year": row["year"], "round": row["round"], "applicants": applicants, "passers": passers, "rate": round(passers / applicants * 100) if applicants else 0}
@app.get("/api/health")
def health():
    return {"ok": True}
@app.post("/api/auth")
def auth(payload: AuthInput):
    pin = payload.pin.strip()
    if not (len(pin) == 4 and pin.isdigit()):
        raise HTTPException(400, "번호는 숫자 네 자리로 입력해 주세요.")
    if payload.action not in ("signup", "login"):
        raise HTTPException(400, "요청을 확인해 주세요.")
    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE pin=?", (pin,)).fetchone()
        if payload.action == "signup":
            if pin == ADMIN_PIN:
                raise HTTPException(403, "관리자 번호는 관리자 모드에서 이용해 주세요.")
            if exists:
                raise HTTPException(409, "이미 가입된 번호예요. 로그인해 주세요.")
            conn.execute("INSERT INTO users(pin) VALUES (?)", (pin,))
        elif not exists:
            raise HTTPException(404, "가입되지 않은 번호예요. 먼저 가입해 주세요.")
    return {"pin": pin, "is_admin": pin == ADMIN_PIN}
@app.get("/api/exam-settings")
def get_exam_settings(exam_type: str = "electric_engineer"):
    validate_exam(exam_type)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM exam_settings_users WHERE user_pin=? AND exam_type=?", (user_pin(), exam_type)).fetchone()
    return setting_dict(row) if row else {"selected_round": None, "round_1_date": "", "round_2_date": "", "round_3_date": ""}
@app.put("/api/exam-settings")
def save_exam_settings(payload: ExamSettingsInput, exam_type: str = "electric_engineer"):
    validate_exam(exam_type)
    if payload.selected_round not in (None, 1, 2, 3):
        raise HTTPException(400, "선택 회차를 확인해 주세요.")
    dates = [payload.round_1_date.strip(), payload.round_2_date.strip(), payload.round_3_date.strip()]
    for value in dates:
        if value:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(400, "시험 날짜 형식을 확인해 주세요.")
    if payload.selected_round and not dates[payload.selected_round - 1]:
        raise HTTPException(400, "선택한 회차의 시험 날짜를 입력해 주세요.")
    pin = user_pin()
    with get_db() as conn:
        conn.execute("""INSERT INTO exam_settings_users(user_pin, exam_type, selected_round, round_1_date, round_2_date, round_3_date, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_pin, exam_type) DO UPDATE SET selected_round=excluded.selected_round,
          round_1_date=excluded.round_1_date, round_2_date=excluded.round_2_date, round_3_date=excluded.round_3_date, updated_at=excluded.updated_at""",
          (pin, exam_type, payload.selected_round, *dates, datetime.now().isoformat(timespec="seconds")))
        row = conn.execute("SELECT * FROM exam_settings_users WHERE user_pin=? AND exam_type=?", (pin, exam_type)).fetchone()
    return setting_dict(row)
@app.get("/api/pass-rates")
def get_pass_rates(exam_type: str = "electric_engineer"):
    validate_exam(exam_type)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM pass_rates WHERE exam_type=? ORDER BY year DESC, round DESC", (exam_type,)).fetchall()
    return [pass_rate_dict(row) for row in rows]
@app.post("/api/pass-rates")
def save_pass_rate(payload: PassRateInput, exam_type: str = "electric_engineer"):
    require_admin()
    validate_exam(exam_type)
    if payload.year not in YEARS or payload.round not in (1, 2, 3):
        raise HTTPException(400, "연도와 회차를 확인해 주세요.")
    if payload.applicants < 0 or payload.passers < 0 or payload.passers > payload.applicants:
        raise HTTPException(400, "응시·합격 인원을 확인해 주세요.")
    with get_db() as conn:
        conn.execute("""INSERT INTO pass_rates(exam_type, year, round, applicants, passers, updated_at) VALUES (?, ?, ?, ?, ?, ?)
          ON CONFLICT(exam_type, year, round) DO UPDATE SET applicants=excluded.applicants, passers=excluded.passers, updated_at=excluded.updated_at""",
          (exam_type, payload.year, payload.round, payload.applicants, payload.passers, datetime.now().isoformat(timespec="seconds")))
        row = conn.execute("SELECT * FROM pass_rates WHERE exam_type=? AND year=? AND round=?", (exam_type, payload.year, payload.round)).fetchone()
    return pass_rate_dict(row)
@app.delete("/api/pass-rates/{rate_id}")
def delete_pass_rate(rate_id: int, exam_type: str = "electric_engineer"):
    require_admin()
    validate_exam(exam_type)
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM pass_rates WHERE id=? AND exam_type=?", (rate_id, exam_type))
    if not cursor.rowcount:
        raise HTTPException(404, "합격률 정보를 찾을 수 없습니다.")
    return {"ok": True}
@app.get("/api/years")
def years(exam_type: str = "electric_engineer"):
    validate_exam(exam_type)
    pin = user_pin()
    with get_db() as conn:
        rows = conn.execute("""SELECT cq.year, COUNT(*) total,
          SUM(CASE WHEN COALESCE(qp.mastered, 0)=1 THEN 1 ELSE 0 END) mastered,
          SUM(CASE WHEN COALESCE(qp.starred, 0)=1 THEN 1 ELSE 0 END) starred,
          SUM(CASE WHEN COALESCE(qp.wrong_count, 0)>=2 THEN 1 ELSE 0 END) difficult
          FROM common_questions cq LEFT JOIN question_progress qp ON qp.question_id=cq.id AND qp.user_pin=?
          WHERE cq.exam_type=? GROUP BY cq.year""", (pin, exam_type)).fetchall()
    lookup = {row["year"]: row for row in rows}
    return [{"year": year, "total": int(lookup[year]["total"]) if year in lookup else 0,
             "mastered": int(lookup[year]["mastered"] or 0) if year in lookup else 0,
             "starred": int(lookup[year]["starred"] or 0) if year in lookup else 0,
             "difficult": int(lookup[year]["difficult"] or 0) if year in lookup else 0} for year in YEARS]
@app.get("/api/questions")
def questions(exam_type: str = "electric_engineer", year: Optional[int] = None, filter: str = "all"):
    validate_exam(exam_type)
    conditions, params = ["cq.exam_type=?"], [user_pin(), exam_type]
    if year is not None:
        conditions.append("cq.year=?")
        params.append(year)
    if filter == "unlearned":
        conditions.append("COALESCE(qp.mastered, 0)=0")
    if filter == "starred":
        conditions.append("COALESCE(qp.starred, 0)=1")
    if filter == "difficult":
        conditions.append("COALESCE(qp.wrong_count, 0)>=2")
    if filter == "mastered":
        conditions.append("COALESCE(qp.mastered, 0)=1")
    with get_db() as conn:
        rows = conn.execute(question_select() + " WHERE " + " AND ".join(conditions) + " ORDER BY cq.year DESC, cq.id DESC", params).fetchall()
    return [question_dict(row) for row in rows]
@app.post("/api/questions")
def create_question(payload: QuestionInput):
    require_admin()
    validate_exam(payload.exam_type)
    if payload.year not in YEARS or not payload.question.strip() or not payload.answer.strip():
        raise HTTPException(400, "연도, 문제, 정답을 확인해 주세요.")
    with get_db() as conn:
        cursor = conn.execute("INSERT INTO common_questions(year, question, answer, explanation, exam_type) VALUES (?, ?, ?, ?, ?)",
          (payload.year, payload.question.strip(), payload.answer.strip(), (payload.explanation or '').strip(), payload.exam_type))
        row = get_question(conn, cursor.lastrowid, user_pin())
    return question_dict(row)
@app.put("/api/questions/{question_id}")
def update_question(question_id: int, payload: QuestionInput):
    require_admin()
    validate_exam(payload.exam_type)
    if payload.year not in YEARS or not payload.question.strip() or not payload.answer.strip():
        raise HTTPException(400, "연도, 문제, 정답을 확인해 주세요.")
    with get_db() as conn:
        cursor = conn.execute("""UPDATE common_questions SET year=?, question=?, answer=?, explanation=COALESCE(?, explanation), updated_at=?
          WHERE id=? AND exam_type=?""", (payload.year, payload.question.strip(), payload.answer.strip(), payload.explanation.strip() if payload.explanation is not None else None, datetime.now().isoformat(timespec="seconds"), question_id, payload.exam_type))
        if not cursor.rowcount:
            raise HTTPException(404, "문제를 찾을 수 없습니다.")
        row = get_question(conn, question_id, user_pin())
    return question_dict(row)
@app.delete("/api/questions/{question_id}")
def delete_question(question_id: int, exam_type: str = "electric_engineer"):
    require_admin()
    validate_exam(exam_type)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM common_questions WHERE id=? AND exam_type=?", (question_id, exam_type)).fetchone()
        if not row:
            raise HTTPException(404, "문제를 찾을 수 없습니다.")
        conn.execute("DELETE FROM learning_records WHERE question_id=?", (question_id,))
        conn.execute("DELETE FROM question_progress WHERE question_id=?", (question_id,))
        conn.execute("DELETE FROM common_questions WHERE id=?", (question_id,))
    return {"ok": True}
def update_flag(question_id: int, exam_type: str, column: str, value: bool):
    validate_exam(exam_type)
    pin = user_pin()
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM common_questions WHERE id=? AND exam_type=?", (question_id, exam_type)).fetchone():
            raise HTTPException(404, "문제를 찾을 수 없습니다.")
        conn.execute(f"""INSERT INTO question_progress(user_pin, question_id, {column}, updated_at) VALUES (?, ?, ?, ?)
          ON CONFLICT(user_pin, question_id) DO UPDATE SET {column}=excluded.{column}, updated_at=excluded.updated_at""", (pin, question_id, int(value), datetime.now().isoformat(timespec="seconds")))
        row = get_question(conn, question_id, pin)
    return question_dict(row)
@app.patch("/api/questions/{question_id}/starred")
def update_starred(question_id: int, payload: FlagInput, exam_type: str = "electric_engineer"):
    return update_flag(question_id, exam_type, "starred", payload.value)
@app.patch("/api/questions/{question_id}/mastered")
def update_mastered(question_id: int, payload: FlagInput, exam_type: str = "electric_engineer"):
    return update_flag(question_id, exam_type, "mastered", payload.value)
@app.post("/api/questions/reset")
def reset_question_progress(exam_type: str = "electric_engineer", year: int = 2026, target: str = "answers"):
    validate_exam(exam_type)
    if year not in YEARS or target not in ("answers", "wrongs"):
        raise HTTPException(400, "초기화 항목을 확인해 주세요.")
    pin = user_pin()
    with get_db() as conn:
        ids = [row["id"] for row in conn.execute("SELECT id FROM common_questions WHERE exam_type=? AND year=?", (exam_type, year)).fetchall()]
        if not ids:
            return {"ok": True, "updated": 0}
        placeholders = ",".join("?" for _ in ids)
        if target == "answers":
            cursor = conn.execute(f"UPDATE question_progress SET last_answer='', updated_at=? WHERE user_pin=? AND question_id IN ({placeholders})", [datetime.now().isoformat(timespec="seconds"), pin, *ids])
        else:
            cursor = conn.execute(f"UPDATE question_progress SET wrong_count=0, updated_at=? WHERE user_pin=? AND question_id IN ({placeholders})", [datetime.now().isoformat(timespec="seconds"), pin, *ids])
            conn.execute(f"DELETE FROM learning_records WHERE user_pin=? AND result='wrong' AND question_id IN ({placeholders})", [pin, *ids])
    return {"ok": True, "updated": cursor.rowcount}
@app.post("/api/questions/{question_id}/review")
def record_review(question_id: int, payload: ReviewInput, exam_type: str = "electric_engineer"):
    validate_exam(exam_type)
    if payload.result not in ("correct", "wrong"):
        raise HTTPException(400, "결과를 선택해 주세요.")
    pin = user_pin()
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM common_questions WHERE id=? AND exam_type=?", (question_id, exam_type)).fetchone():
            raise HTTPException(404, "문제를 찾을 수 없습니다.")
        conn.execute("INSERT INTO learning_records(question_id, user_pin, answer_text, result) VALUES (?, ?, ?, ?)", (question_id, pin, payload.answer_text.strip(), payload.result))
        conn.execute("""INSERT INTO question_progress(user_pin, question_id, last_answer, wrong_count, updated_at) VALUES (?, ?, ?, ?, ?)
          ON CONFLICT(user_pin, question_id) DO UPDATE SET last_answer=excluded.last_answer,
          wrong_count=question_progress.wrong_count+excluded.wrong_count, updated_at=excluded.updated_at""", (pin, question_id, payload.answer_text.strip(), 1 if payload.result == "wrong" else 0, datetime.now().isoformat(timespec="seconds")))
        updated = get_question(conn, question_id, pin)
    return question_dict(updated)
@app.get("/api/stats")
def stats(exam_type: str = "electric_engineer"):
    validate_exam(exam_type)
    pin = user_pin()
    with get_db() as conn:
        totals = conn.execute("""SELECT COUNT(*) total, SUM(CASE WHEN COALESCE(qp.mastered,0)=1 THEN 1 ELSE 0 END) mastered,
          SUM(CASE WHEN COALESCE(qp.starred,0)=1 THEN 1 ELSE 0 END) starred, SUM(COALESCE(qp.wrong_count,0)) wrongs
          FROM common_questions cq LEFT JOIN question_progress qp ON qp.question_id=cq.id AND qp.user_pin=? WHERE cq.exam_type=?""", (pin, exam_type)).fetchone()
        recent = conn.execute("""SELECT lr.*, cq.question, cq.year FROM learning_records lr JOIN common_questions cq ON cq.id=lr.question_id
          WHERE lr.user_pin=? AND cq.exam_type=? ORDER BY lr.id DESC LIMIT 6""", (pin, exam_type)).fetchall()
    return {"total": totals["total"], "mastered": totals["mastered"] or 0, "starred": totals["starred"] or 0, "wrongs": totals["wrongs"] or 0, "recent": [dict(row) for row in recent]}
@app.get("/api/helper")
def helper_history():
    with get_db() as conn:
        rows = conn.execute("SELECT id, role, text FROM helper_messages WHERE user_pin=? ORDER BY id DESC LIMIT 30", (user_pin(),)).fetchall()
    return [dict(row) for row in reversed(rows)]
def save_helper_message(role: str, text: str):
    with get_db() as conn:
        cursor = conn.execute("INSERT INTO helper_messages(user_pin, role, text) VALUES (?, ?, ?)", (user_pin(), role, text))
        return dict(conn.execute("SELECT id, role, text FROM helper_messages WHERE id=?", (cursor.lastrowid,)).fetchone())
def response_text(payload: dict) -> str:
    return "\n".join(content["text"] for item in payload.get("output", []) for content in item.get("content", []) if content.get("type") == "output_text" and content.get("text")).strip()
@app.post("/api/helper")
def helper(payload: dict):
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(400, "질문을 입력해 주세요.")
    if len(question) > 1000:
        raise HTTPException(400, "질문은 1,000자 이내로 입력해 주세요.")
    user_message = save_helper_message("user", question)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "챗GPT 연결을 위해 OPENAI_API_KEY 설정이 필요해요.")
    with get_db() as conn:
        history = conn.execute("SELECT role, text FROM helper_messages WHERE user_pin=? ORDER BY id DESC LIMIT 12", (user_pin(),)).fetchall()
    request_data = json.dumps({"model": os.environ.get("OPENAI_MODEL", "gpt-5-mini"), "instructions": "당신은 전기기사와 전기공사기사 실기 단답형 학습 도우미입니다. 한국어로 간결하게 답하고, 계산 문제는 핵심 개념과 암기 포인트를 설명합니다.", "input": [{"role": row["role"], "content": row["text"]} for row in reversed(history)]}).encode("utf-8")
    request = urllib.request.Request("https://api.openai.com/v1/responses", data=request_data, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            answer = response_text(json.loads(response.read().decode("utf-8")))
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise HTTPException(503, "챗GPT 인증 정보를 확인해 주세요.")
        if error.code == 429:
            raise HTTPException(503, "챗GPT 요청 한도에 도달했어요. 잠시 후 다시 시도해 주세요.")
        raise HTTPException(503, "챗GPT 답변을 가져오지 못했어요. 잠시 후 다시 시도해 주세요.")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise HTTPException(503, "챗GPT 연결이 지연되고 있어요. 잠시 후 다시 시도해 주세요.")
    if not answer:
        raise HTTPException(503, "챗GPT가 답변을 만들지 못했어요. 질문을 조금 바꿔 주세요.")
    return {"user": user_message, "assistant": save_helper_message("assistant", answer)}
