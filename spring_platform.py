import os
import re
import sqlite3
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DB_PATH = os.getenv("SPRINGBOT_DB", "springbot_v2.db")
ADMIN_KEY = os.getenv("SPRINGBOT_ADMIN_KEY", "change-me")

client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None

app = FastAPI(title="SpringBot AI Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM = """
You are SpringBot Platform AI: an AI operations system for Discord communities, virtual offices,
IT support, cybersecurity study, automation workflows, knowledge bases, and business productivity.
Be direct, practical, secure, and action-oriented.
Never expose secrets, tokens, API keys, or private environment variables.
"""

AGENTS = {
    "support": "You are SpringBot Support Agent. Diagnose user problems, ask only necessary questions, and provide step-by-step fixes.",
    "moderation": "You are SpringBot Moderation Agent. Identify risks, scams, harassment, spam, and recommend safe admin actions.",
    "study": "You are SpringBot Study Agent. Teach IT, cybersecurity, networking, A+, Security+, and AI concepts clearly.",
    "business": "You are SpringBot Business Agent. Create plans, SOPs, scripts, emails, workflows, and monetization strategy.",
    "coding": "You are SpringBot Coding Agent. Help debug, write, explain, and improve code with safe complete examples.",
    "general": "You are SpringBot General Agent. Be helpful, clear, and concise.",
}

WORKFLOW_TEMPLATES = {
    "new_member_onboarding": [
        "Greet the new member",
        "Explain server purpose",
        "Share rules and support channel",
        "Recommend first 3 actions",
        "Invite them to ask SpringBot for help",
    ],
    "support_ticket": [
        "Collect problem summary",
        "Ask for device/app/error details",
        "Classify priority",
        "Suggest first troubleshooting steps",
        "Escalate if unresolved",
    ],
    "phishing_response": [
        "Delete or quarantine risky message",
        "Log incident",
        "Warn user/admins",
        "Check similar messages",
        "Post safety reminder if needed",
    ],
    "daily_operations": [
        "Summarize activity",
        "List unresolved issues",
        "Identify risks",
        "Recommend next actions",
        "Generate admin brief",
    ],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    with db_connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS platform_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            name TEXT NOT NULL,
            trigger_name TEXT NOT NULL,
            steps TEXT NOT NULL,
            enabled TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS voice_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            status TEXT NOT NULL,
            transcript TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.commit()


def verify_admin(key: Optional[str]):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


def chunk_text(text: str, size: int = 12000) -> List[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def search_kb(query: str, guild_id: str = "global", limit: int = 5) -> str:
    terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9+#.-]{3,}", query or "")]
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT title, body FROM knowledge_base WHERE guild_id IN (?, 'global') ORDER BY id DESC LIMIT 200",
            (str(guild_id),),
        ).fetchall()

    scored = []
    for row in rows:
        full = f"{row['title']} {row['body']}".lower()
        score = sum(1 for t in terms if t in full)
        if score:
            scored.append((score, row["title"], row["body"]))
    scored.sort(reverse=True, key=lambda x: x[0])
    return "\n\n".join([f"Title: {title}\n{body[:1500]}" for _, title, body in scored[:limit]])


async def run_agent(agent: str, message: str, user_id: str = "web", guild_id: str = "global") -> str:
    if agent not in AGENTS:
        agent = "general"

    kb = search_kb(message, guild_id=guild_id)
    if not client:
        return "AI is not connected. Add OPENAI_API_KEY to the environment."

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "system", "content": AGENTS[agent]},
        {"role": "system", "content": f"Relevant knowledge base:\n{kb or 'No relevant knowledge-base entries.'}"},
        {"role": "user", "content": message},
    ]

    try:
        result = await asyncio.to_thread(
            client.chat.completions.create,
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.65,
        )
        response = result.choices[0].message.content.strip()
    except Exception as e:
        response = f"AI error: {e}"

    with db_connect() as conn:
        conn.execute(
            "INSERT INTO platform_chats (agent, user_id, message, response, created_at) VALUES (?, ?, ?, ?, ?)",
            (agent, user_id, message[:5000], response[:10000], now_iso()),
        )
        conn.commit()

    return response


class ChatRequest(BaseModel):
    message: str
    agent: str = "general"
    user_id: str = "web"
    guild_id: str = "global"


class KBRequest(BaseModel):
    title: str
    body: str
    guild_id: str = "global"
    created_by: str = "web"
    admin_key: str


class WorkflowRequest(BaseModel):
    guild_id: str = "global"
    name: str
    trigger_name: str
    steps: List[str]
    enabled: bool = True
    admin_key: str


class VoiceSessionRequest(BaseModel):
    guild_id: str
    channel_id: str
    transcript: str = ""
    status: str = "ready"
    admin_key: str


@app.on_event("startup")
async def startup():
    setup_database()


@app.get("/health")
async def health():
    return {"status": "online", "service": "SpringBot AI Platform", "ai_connected": bool(client)}


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>SpringBot AI Platform</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { margin:0; font-family: Arial, sans-serif; background:#07110d; color:#e9fff1; }
    .wrap { max-width:1100px; margin:auto; padding:32px; }
    .hero { padding:36px; border:1px solid rgba(120,255,170,.25); border-radius:24px; background:linear-gradient(135deg, rgba(27,80,52,.8), rgba(10,17,14,.9)); box-shadow:0 0 40px rgba(0,255,130,.12); }
    h1 { font-size:42px; margin:0 0 12px; }
    p { color:#bde8cc; line-height:1.6; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:16px; margin-top:24px; }
    .card { padding:20px; border:1px solid rgba(120,255,170,.18); border-radius:18px; background:rgba(255,255,255,.04); }
    .tag { display:inline-block; padding:6px 10px; border-radius:99px; background:#113d27; color:#9cffbd; font-size:13px; margin:4px; }
    code { background:#0f2018; padding:3px 6px; border-radius:6px; color:#9cffbd; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>🌸 SpringBot AI Platform</h1>
      <p>AI memory, Discord operations, moderation, support tickets, knowledge base, workflows, voice-ready sessions, and Spring Virtual Office features.</p>
      <span class="tag">AI Agents</span><span class="tag">RAG Foundation</span><span class="tag">Moderation</span><span class="tag">Workflows</span><span class="tag">Voice Ready</span>
    </div>
    <div class="grid">
      <div class="card"><h3>AI Agents</h3><p>Support, moderation, study, business, coding, and general agents.</p><code>POST /api/chat</code></div>
      <div class="card"><h3>Knowledge Base</h3><p>Store and search docs/notes for AI answers.</p><code>POST /api/kb</code></div>
      <div class="card"><h3>Workflows</h3><p>Templates for onboarding, tickets, phishing response, and daily operations.</p><code>GET /api/workflows/templates</code></div>
      <div class="card"><h3>Voice Sessions</h3><p>Backend structure for Jarvis-style voice mode.</p><code>POST /api/voice/session</code></div>
    </div>
  </div>
</body>
</html>
"""


@app.post("/api/chat")
async def chat(req: ChatRequest):
    response = await run_agent(req.agent, req.message, req.user_id, req.guild_id)
    return {"agent": req.agent, "response": response}


@app.get("/api/agents")
async def agents():
    return {"agents": list(AGENTS.keys()), "details": AGENTS}


@app.post("/api/kb")
async def add_kb(req: KBRequest):
    verify_admin(req.admin_key)
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO knowledge_base (guild_id, title, body, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (req.guild_id, req.title[:160], req.body[:20000], req.created_by, now_iso()),
        )
        conn.commit()
    return {"status": "saved", "title": req.title}


@app.get("/api/kb/search")
async def kb_search(query: str, guild_id: str = "global"):
    return {"query": query, "results": search_kb(query, guild_id)}


@app.post("/api/kb/upload")
async def upload_kb(admin_key: str = Form(...), guild_id: str = Form("global"), title: str = Form(...), file: UploadFile = File(...)):
    verify_admin(admin_key)
    raw = await file.read()
    try:
        body = raw.decode("utf-8")
    except Exception:
        body = raw.decode("latin-1", errors="ignore")

    with db_connect() as conn:
        for idx, chunk in enumerate(chunk_text(body, 12000), start=1):
            conn.execute(
                "INSERT INTO knowledge_base (guild_id, title, body, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                (guild_id, f"{title} - Part {idx}", chunk, "upload", now_iso()),
            )
        conn.commit()

    return {"status": "uploaded", "title": title, "parts": len(chunk_text(body, 12000))}


@app.get("/api/workflows/templates")
async def workflow_templates():
    return WORKFLOW_TEMPLATES


@app.post("/api/workflows")
async def create_workflow(req: WorkflowRequest):
    verify_admin(req.admin_key)
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO workflows (guild_id, name, trigger_name, steps, enabled, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (req.guild_id, req.name, req.trigger_name, "\n".join(req.steps), "true" if req.enabled else "false", now_iso()),
        )
        conn.commit()
    return {"status": "created", "workflow": req.name}


@app.get("/api/workflows")
async def list_workflows(guild_id: str = "global"):
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT id, name, trigger_name, steps, enabled, created_at FROM workflows WHERE guild_id=? ORDER BY id DESC",
            (guild_id,),
        ).fetchall()
    return {"workflows": [dict(row) for row in rows]}


@app.post("/api/voice/session")
async def create_voice_session(req: VoiceSessionRequest):
    verify_admin(req.admin_key)
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO voice_sessions (guild_id, channel_id, status, transcript, created_at) VALUES (?, ?, ?, ?, ?)",
            (req.guild_id, req.channel_id, req.status, req.transcript, now_iso()),
        )
        conn.commit()
    return {"status": "voice-session-created", "mode": "voice-ready"}


@app.get("/api/stats")
async def stats():
    with db_connect() as conn:
        data = {
            "platform_chats": conn.execute("SELECT COUNT(*) AS c FROM platform_chats").fetchone()["c"],
            "knowledge_items": conn.execute("SELECT COUNT(*) AS c FROM knowledge_base").fetchone()["c"],
            "workflows": conn.execute("SELECT COUNT(*) AS c FROM workflows").fetchone()["c"],
            "voice_sessions": conn.execute("SELECT COUNT(*) AS c FROM voice_sessions").fetchone()["c"],
        }
    return data


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("spring_platform:app", host="0.0.0.0", port=port, reload=False)
