from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3, uuid, re, json, os
from datetime import datetime, timezone
from collections import Counter

DB_PATH = Path(os.getenv("BAXI_DB", "baxi.sqlite3"))
app = FastAPI(title="Baxi AI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS messages(
          id TEXT PRIMARY KEY, user_text TEXT NOT NULL, answer TEXT NOT NULL,
          topic TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feedback(
          id INTEGER PRIMARY KEY AUTOINCREMENT, message_id TEXT NOT NULL,
          rating INTEGER NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS knowledge(
          id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL,
          answer TEXT NOT NULL, hits INTEGER NOT NULL DEFAULT 0,
          score REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL
        );
        """)
init_db()

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    history: list[dict] = []

class FeedbackRequest(BaseModel):
    message_id: str | None = None
    rating: int = Field(ge=-1, le=1)

class KnowledgeRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    answer: str = Field(min_length=1, max_length=5000)

def now():
    return datetime.now(timezone.utc).isoformat()

def tokens(s):
    return set(re.findall(r"[а-яёa-z0-9]{3,}", s.lower()))

def topic_for(text):
    words = tokens(text)
    groups = {
        "программирование": {"python","код","html","css","javascript","программ","сайт","бот","апк"},
        "учёба": {"задач","математ","физик","хими","истори","учёб","школ","объясни"},
        "творчество": {"идея","истори","стих","дизайн","назван","придум"},
        "технологии": {"телефон","компьютер","ии","нейросет","приложен","интернет"},
    }
    for name, keys in groups.items():
        if any(k in text.lower() for k in keys) or words & keys:
            return name
    return "общее"

def retrieve(question):
    q = tokens(question)
    if not q: return None
    with db() as con:
        rows = con.execute("SELECT id,question,answer,hits,score FROM knowledge").fetchall()
        best, best_score = None, 0.0
        for row in rows:
            t = tokens(row["question"])
            similarity = len(q & t) / max(1, len(q | t))
            adjusted = similarity * (1 + min(row["score"], 5) * .04)
            if adjusted > best_score:
                best, best_score = row, adjusted
        if best and best_score >= .22:
            con.execute("UPDATE knowledge SET hits=hits+1 WHERE id=?", (best["id"],))
            return best["answer"]
    return None

def make_answer(message):
    learned = retrieve(message)
    if learned:
        return learned
    s = message.lower()
    if any(x in s for x in ["привет", "здравств", "добрый день"]):
        return "Привет! Я Baxi. Расскажи, чем могу помочь: объяснить тему, разобраться с кодом, придумать идею или подготовить текст."
    if "кто ты" in s or "что ты умеешь" in s:
        return "Я Baxi — ИИ-помощник с Python API. Я сохраняю историю запросов, анализирую темы и оценки ответов, а также могу использовать пополняемую базу знаний. Для генеративных ответов подключи языковую модель на серверной стороне."
    if any(x in s for x in ["python", "код", "программ", "html", "css", "javascript"]):
        return "Могу помочь с программированием. Напиши, что именно нужно получить, на каком языке и покажи ошибку или текущий код — разберём по шагам."
    if "спасибо" in s:
        return "Пожалуйста! Если ответ был полезен, оцени его кнопкой 👍 — это поможет улучшать базу знаний Baxi."
    return ("Я получил вопрос и сохранил его в аналитике. Сейчас включён базовый режим: он использует шаблоны и накопленную базу знаний, "
            "а не большую генеративную нейросеть. Добавь проверенный ответ в базу знаний через /knowledge, чтобы Baxi мог использовать его в похожих вопросах.")

@app.get("/health")
def health():
    return {"ok": True, "service": "Baxi AI API", "version": "1.0.0"}

@app.post("/chat")
def chat(req: ChatRequest):
    message = req.message.strip()
    if not message:
        raise HTTPException(400, "Пустое сообщение")
    answer = make_answer(message)
    msg_id = str(uuid.uuid4())
    with db() as con:
        con.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                    (msg_id, message, answer, topic_for(message), now()))
    return {"message_id": msg_id, "answer": answer, "topic": topic_for(message)}

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    if not req.message_id:
        return {"ok": False, "detail": "message_id is required"}
    with db() as con:
        exists = con.execute("SELECT id FROM messages WHERE id=?", (req.message_id,)).fetchone()
        if not exists:
            raise HTTPException(404, "Сообщение не найдено")
        con.execute("INSERT INTO feedback(message_id,rating,created_at) VALUES(?,?,?)",
                    (req.message_id, req.rating, now()))
    return {"ok": True}

@app.post("/knowledge")
def add_knowledge(req: KnowledgeRequest):
    with db() as con:
        con.execute("INSERT INTO knowledge(question,answer,created_at) VALUES(?,?,?)",
                    (req.question.strip(), req.answer.strip(), now()))
    return {"ok": True, "detail": "Запись добавлена в базу знаний"}

@app.get("/analytics")
def analytics():
    with db() as con:
        total = con.execute("SELECT COUNT(*) n FROM messages").fetchone()["n"]
        known = con.execute("SELECT COUNT(*) n FROM knowledge").fetchone()["n"]
        positive = con.execute("SELECT COUNT(*) n FROM feedback WHERE rating=1").fetchone()["n"]
        negative = con.execute("SELECT COUNT(*) n FROM feedback WHERE rating=-1").fetchone()["n"]
        topics = con.execute("SELECT topic,COUNT(*) n FROM messages GROUP BY topic ORDER BY n DESC LIMIT 5").fetchall()
    return {"total_messages": total, "known_answers": known,
            "positive_feedback": positive, "negative_feedback": negative,
            "top_topics": [{"topic": r["topic"], "count": r["n"]} for r in topics]}

@app.get("/")
def root():
    return {"message": "Baxi AI API is running", "docs": "/docs"}
