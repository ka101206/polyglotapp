import os
import json
import base64
import re
import asyncio
import random
import traceback

import bcrypt
import pykakasi
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

import config
from database import init_db, get_db, SessionLocal, User, Message, Vocabulary
from analytics import AnalyticsManager
from ai_client import AIClient
from tts_engine import TTSEngine

# ---------- App setup ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Singletons ----------

ai_client = AIClient()
tts_engine = TTSEngine()
_kakasi = pykakasi.kakasi()  # Reuse a single instance

# ---------- Auth ----------

class AuthRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    user_id: int
    username: str
    message: str
    avatar: str | None = None
    nickname: str | None = None

class UserUpdateRequest(BaseModel):
    username: str | None = None
    avatar: str | None = None
    nickname: str | None = None

@app.post("/auth/register", response_model=AuthResponse)
def register(req: AuthRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    new_user = User(username=req.username, password_hash=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"user_id": new_user.id, "username": new_user.username, "message": "Registered successfully", "avatar": new_user.avatar, "nickname": new_user.nickname}

@app.post("/auth/login", response_model=AuthResponse)
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not bcrypt.checkpw(req.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user_id": user.id, "username": user.username, "message": "Logged in successfully", "avatar": user.avatar, "nickname": user.nickname}

@app.put("/api/users/{user_id}", response_model=AuthResponse)
def update_user(user_id: int, req: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
        
    if req.username and req.username != user.username:
        if db.query(User).filter(User.username == req.username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = req.username
        
    if req.avatar is not None:
        user.avatar = req.avatar
        
    if req.nickname is not None:
        user.nickname = req.nickname
        
    db.commit()
    return {"user_id": user.id, "username": user.username, "message": "Updated successfully", "avatar": user.avatar, "nickname": user.nickname}

# ---------- Analytics ----------

@app.get("/api/analytics/{user_id}")
def get_analytics(user_id: int, db: Session = Depends(get_db)):
    manager = AnalyticsManager(db, user_id)
    summary = manager.get_summary()
    if not summary:
        return {"total_speaking_time_minutes": 0, "total_mistakes": 0, "avg_fluency_score": 0, "avg_grammar_score": 0, "avg_listening_score": 0}
    return summary

@app.get("/health")
def health():
    return {"status": "ok"}

# ---------- Text helpers ----------

def strip_romaji(text: str) -> str:
    return re.sub(r'\s*\(([a-zA-Z][a-zA-Z0-9\s\-\x27,.!?]*)\)', '', text)

def dedup_repeated_phrases(text: str) -> str:
    text = re.sub(r'\b(.{3,60}?)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(.{3,60}?)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    return text

def apply_reading_mode(text: str, language: str, reading_mode: str) -> str:
    if language == "Japanese" and reading_mode in ("ふりがな", "かなのみ"):
        result = _kakasi.convert(text)
        if reading_mode == "ふりがな":
            return "".join(
                f"<ruby>{item['orig']}<rt>{item['hira']}</rt></ruby>" if item['orig'] != item['hira'] else item['orig']
                for item in result
            )
        else:  # かなのみ
            return "".join(item['hira'] for item in result)
    elif language == "Chinese" and reading_mode == "拼音":
        try:
            from pypinyin import pinyin, Style
            chars = list(text)
            py = pinyin(text, style=Style.TONE)
            out = []
            for ch, p in zip(chars, py):
                tone = p[0]
                if ch != tone and '\u4e00' <= ch <= '\u9fff':
                    out.append(f"<ruby>{ch}<rt>{tone}</rt></ruby>")
                else:
                    out.append(ch)
            return "".join(out)
        except ImportError:
            return text
    return text

def needs_furigana(reading_mode: str) -> bool:
    return reading_mode in ("ふりがな", "かなのみ", "拼音")

# ---------- WebSocket ----------

@app.websocket("/ws/chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    db = next(get_db())
    analytics_manager = AnalyticsManager(db, user_id)
    scenario_grammar_errors = []
    # Per-connection AI client to isolate user state (history, nickname, register)
    ai_client = AIClient()

    async def send_audio(text, speed, language, gender="female"):
        """Generate and send audio for a single sentence."""
        async for audio_bytes in tts_engine.generate_audio_stream(text, speed=speed, language=language, gender=gender):
            encoded = base64.b64encode(audio_bytes).decode()
            await websocket.send_json({"type": "audio", "data": encoded})

    async def fetch_word_bank(reply_text, lang, diff):
        if "Advanced" in diff:
            return
            
        include_decoys = "Elementary" in diff
        words, ok = await ai_client.generate_word_bank(reply_text, lang, include_decoys)
        if ok and words:
            await websocket.send_json({"type": "word_bank", "words": words})

    async def fetch_grammar(user_text, lang, diff, scenario):
        grammar, ok = await ai_client.analyze_grammar(user_text, lang, diff)
        print(f"[DEBUG] fetch_grammar output: '{grammar}'", flush=True)
        if ok and grammar:
            if grammar.strip() != "PERFECT":
                analytics_manager.add_mistake()
                if scenario:
                    scenario_grammar_errors.append(grammar)
            await websocket.send_json({"type": "grammar", "content": grammar})

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            msg_type = payload.get("type", "chat")

            # --- Tutor Chat ---
            if msg_type == "tutor_chat":
                question = payload.get("question", "")
                original_text = payload.get("original_text", "")
                grammar_correction = payload.get("grammar_correction", "")
                history = payload.get("history", [])
                target_language = payload.get("language", "Japanese")
                reading_mode = payload.get("readingMode", "なし")

                reply = await ai_client.chat_with_grammar_tutor(question, original_text, grammar_correction, history, target_language)
                reply = dedup_repeated_phrases(reply)
                if target_language == "Japanese":
                    reply = strip_romaji(reply)
                display = apply_reading_mode(reply, target_language, reading_mode)
                await websocket.send_json({"type": "tutor_reply", "content": display})
                continue

            # --- Repeat Audio ---
            if msg_type == "repeat":
                text_to_repeat = payload.get("text", "")
                req_lang = payload.get("language", "Japanese")
                req_speed = float(payload.get("speed", 0.8))
                req_gender = payload.get("gender", "female")
                await send_audio(text_to_repeat, req_speed, req_lang, req_gender)
                await websocket.send_json({"type": "audio_done"})
                continue

            # --- Start Scenario ---
            if msg_type == "start_scenario":
                scenario_name = payload.get("scenario")
                language = payload.get("language", "Japanese")
                difficulty = payload.get("difficulty", "Intermediate")
                reading_mode = payload.get("reading_mode", "なし")
                scenario_dict = config.SCENARIOS.get(scenario_name)
                scenario_grammar_errors = []

                cached_list = scenario_dict.get("cached_intros", {}).get(language)
                if not cached_list:
                    await websocket.send_json({"type": "error", "content": "Intro not found."})
                    continue

                reply = random.choice(cached_list)
                ai_client.start_scenario(reply)
                display = apply_reading_mode(reply, language, reading_mode)

                await websocket.send_json({"type": "scenario_start", "scenario": scenario_name, "goal": scenario_dict["user_goal"]})
                await websocket.send_json({"type": "text", "content": display, "raw_content": reply})

                req_speed = float(payload.get("speed", 1.0))
                req_gender = payload.get("gender", "female")
                await send_audio(reply, req_speed, language, req_gender)
                await websocket.send_json({"type": "audio_done"})
                
                enable_word_bank = payload.get("enable_word_bank", True)
                if enable_word_bank:
                    asyncio.create_task(fetch_word_bank(reply, language, difficulty))
                continue

            # --- Normal / Scenario Chat ---
            user_text = payload.get("text", "")
            language = payload.get("language", "Japanese")
            difficulty = payload.get("difficulty", "Intermediate")
            scenario = payload.get("scenario")
            reading_mode = payload.get("reading_mode", "なし")
            req_speed = float(payload.get("speed", 1.0))
            enable_grammar = payload.get("enable_grammar", True)
            enable_word_bank = payload.get("enable_word_bank", True)
            req_gender = payload.get("gender", "female")
            print(f"[DEBUG] Chat payload received: enable_grammar={enable_grammar}")

            # Track speaking analytics
            duration = payload.get("duration")
            db_user = db.query(User).filter(User.id == user_id).first()
            if duration:
                if db_user:
                    db_user.total_chars_spoken += len(user_text)
                    db_user.total_seconds_spoken += duration
                    if db_user.total_seconds_spoken > 0:
                        db_user.avg_chars_per_second = db_user.total_chars_spoken / db_user.total_seconds_spoken
                    db.commit()
                analytics_manager.add_speaking_time(duration)
            else:
                avg = db_user.avg_chars_per_second if db_user and db_user.avg_chars_per_second > 0 else 5.0
                analytics_manager.add_speaking_time(len(user_text) / avg)

            # Pick the right generator
            user_name = None
            if db_user:
                user_name = db_user.nickname or db_user.username
                
            if scenario:
                scenario_dict = config.SCENARIOS.get(scenario)
                generator = ai_client.get_scenario_reply_stream(user_text, language, difficulty, scenario_dict, enable_grammar, enable_word_bank, user_name=user_name)
            else:
                generator = ai_client.get_reply_stream(user_text, language, difficulty, enable_grammar, enable_word_bank, user_name=user_name)

            # --- Stream LLM → UI + Audio ---
            use_furigana = needs_furigana(reading_mode)
            audio_queue = asyncio.Queue()
            final_full_reply = ""
            goal_reached = False
            success = False

            async def _audio_worker():
                while True:
                    chunk = await audio_queue.get()
                    if chunk is None:
                        break
                    await send_audio(chunk, req_speed, language, req_gender)

            audio_task = asyncio.create_task(_audio_worker())

            async for text_delta, sentence, full_reply, ok, done, extras in generator:
                if not ok:
                    await websocket.send_json({"type": "error", "content": text_delta})
                    break

                if done:
                    final_full_reply = full_reply
                    success = True
                    if extras.get("goal_reached"):
                        goal_reached = True
                    break

                # Stream text to UI
                if text_delta and not use_furigana:
                    await websocket.send_json({"type": "text", "content": text_delta, "raw_content": text_delta})

                # When a full sentence is ready
                if sentence:
                    clean = ai_client._cleanup_text(sentence)
                    if not clean:
                        continue

                    # If furigana mode, send the processed sentence now
                    if use_furigana:
                        display = apply_reading_mode(clean, language, reading_mode)
                        await websocket.send_json({"type": "text", "content": display, "raw_content": clean})

                    await audio_queue.put(clean)

            # Shut down audio worker
            await audio_queue.put(None)
            await audio_task

            if success:
                await websocket.send_json({"type": "audio_done"})

                if final_full_reply:
                    clean_reply = final_full_reply.replace("[GOAL_REACHED]", "").strip()
                    print(f"[DEBUG] Creating fetch tasks. enable_grammar={enable_grammar}", flush=True)
                    if enable_grammar:
                        asyncio.create_task(fetch_grammar(user_text, language, difficulty, scenario))
                    if enable_word_bank:
                        asyncio.create_task(fetch_word_bank(clean_reply, language, difficulty))

                if goal_reached or "[GOAL_REACHED]" in (final_full_reply or ""):
                    analytics_manager.add_fluency_score(random.randint(70, 95))
                    analytics_manager.add_grammar_score(random.randint(70, 95))
                    analytics_manager.add_listening_score(random.randint(70, 95))

                    critique = (
                        "Great job! You completed the scenario with perfect grammar."
                        if not scenario_grammar_errors
                        else "Scenario completed! Here are some grammar corrections from this session:\n\n"
                             + "\n".join(f"{i}. {err}" for i, err in enumerate(scenario_grammar_errors, 1))
                    )
                    await websocket.send_json({"type": "scenario_complete", "critique": critique})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket Error: {e}", flush=True)
        traceback.print_exc()
    finally:
        print(f"Client {user_id} disconnected", flush=True)

# ---------- REST endpoints ----------

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return {"success": True}
        return {"error": "Not found"}
    finally:
        db.close()

@app.post("/api/ai/definition")
async def get_definition(payload: dict):
    word = payload.get("word")
    context = payload.get("context", "")
    language = payload.get("language", "Japanese")
    definition = await ai_client.get_definition(word, context, language)
    return {"definition": definition}

@app.post("/api/audio/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    from stt_engine import STTEngine
    stt = STTEngine()
    audio_bytes = await file.read()
    text = stt.transcribe_audio(audio_bytes)
    return {"text": text}

@app.get("/api/notebook")
async def get_notebook(user_id: int):
    db = SessionLocal()
    try:
        vocab = db.query(Vocabulary).filter(Vocabulary.user_id == user_id).order_by(Vocabulary.first_seen_at.desc()).all()
        return [{"id": v.id, "word": v.word, "definition": v.definition, "created_at": v.first_seen_at.isoformat() if v.first_seen_at else None} for v in vocab]
    finally:
        db.close()

@app.post("/api/notebook")
async def add_notebook_entry(payload: dict):
    user_id = payload.get("user_id")
    word = payload.get("word")
    definition = payload.get("definition")
    if not all([user_id, word, definition]):
        return {"error": "Missing required fields"}
    db = SessionLocal()
    try:
        new_vocab = Vocabulary(user_id=user_id, word=word, definition=definition)
        db.add(new_vocab)
        db.commit()
        db.refresh(new_vocab)
        return {"id": new_vocab.id, "word": new_vocab.word, "definition": new_vocab.definition, "created_at": new_vocab.first_seen_at.isoformat() if new_vocab.first_seen_at else None}
    finally:
        db.close()

@app.delete("/api/notebook/{vocab_id}")
async def delete_notebook_entry(vocab_id: int):
    db = SessionLocal()
    try:
        vocab = db.query(Vocabulary).filter(Vocabulary.id == vocab_id).first()
        if vocab:
            db.delete(vocab)
            db.commit()
            return {"success": True}
        return {"error": "Not found"}
    finally:
        db.close()