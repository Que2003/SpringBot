# SpringBot V2 Setup

## New Features
- AI memory system
- AI actions
- Ticket system
- Server health analysis
- Channel summarization
- AI study system
- Persistent SQLite memory database
- Smarter Discord AI replies

---

## Files Added
- `bot_v2.py`

---

## Install Dependencies

```bash
pip install -r requirements.txt
pip install sqlite3
```

---

## Add Environment Variables

### Railway / Render / VPS

```env
DISCORD_TOKEN=your_token_here
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
SPRINGBOT_PREFIX=!
```

---

## Start SpringBot V2

```bash
python bot_v2.py
```

---

## Important Commands

### AI
- `!springai <message>`
- Mention SpringBot directly

### Memory
- `!remember favorite_game = Black Myth Wukong`
- `!memory`
- `!forget favorite_game`
- `!forgetme`

### AI Actions
- `!actions`
- `!do create_ticket Need help with networking`
- `!do server_health`
- `!do study_quiz Security+`
- `!do summarize_channel`

### Admin
- `!serverhealth`
- `!ticket`
- `!summarize`

---

## Recommended Next Upgrades

### Phase 2
- Voice AI assistant
- Live web search
- AI moderation
- AI onboarding
- AI role assignment
- Knowledge-base uploads (RAG)
- Web dashboard
- PostgreSQL migration
- Vector database memory

### Phase 3
- Mobile app
- Spring Virtual Office SaaS panel
- AI workflows
- AI support agents
- Multi-model routing
- Real-time voice conversations

---

## Recommended Stack
- Python
- FastAPI
- Discord.py
- OpenAI API
- SQLite -> PostgreSQL later
- Railway hosting
- Docker
- React frontend later
