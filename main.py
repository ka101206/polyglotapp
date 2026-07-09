import os
import json
import base64
import re
import asyncio
import random
import traceback
import uuid
from datetime import datetime, timedelta

import bcrypt
import pykakasi
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

import config
from database import init_db, get_db, SessionLocal, User, Message, Vocabulary, Group, ConversationSession, GroupInvite
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
    is_admin: bool = False

class AuthResponse(BaseModel):
    user_id: int
    username: str
    message: str
    avatar: str | None = None
    nickname: str | None = None
    is_admin: bool = False

class UserUpdateRequest(BaseModel):
    username: str | None = None
    avatar: str | None = None
    nickname: str | None = None

@app.post("/auth/register", response_model=AuthResponse)
def register(req: AuthRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    
    new_user = User(username=req.username, password_hash=hashed, is_admin=req.is_admin)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"user_id": new_user.id, "username": new_user.username, "message": "Registered successfully", "avatar": new_user.avatar, "nickname": new_user.nickname, "is_admin": new_user.is_admin}

@app.post("/auth/login", response_model=AuthResponse)
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not bcrypt.checkpw(req.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user_id": user.id, "username": user.username, "message": "Logged in successfully", "avatar": user.avatar, "nickname": user.nickname, "is_admin": user.is_admin}

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

# ---------- Debug dashboard ----------

@app.get("/api/debug/status")
async def debug_status():
    from debug_status import collect_status
    return await collect_status(ai_client, tts_engine)

@app.get("/debug", response_class=HTMLResponse)
def debug_dashboard():
    from debug_status import DEBUG_HTML
    return DEBUG_HTML

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
    db = SessionLocal()
    analytics_manager = AnalyticsManager(db, user_id)
    scenario_grammar_errors = []
    # Per-connection AI client to isolate user state (history, nickname, register)
    ai_client = AIClient()
    
    session_id = str(uuid.uuid4())
    conv_session = ConversationSession(id=session_id, user_id=user_id)
    db.add(conv_session)
    db.commit()

    async def send_audio(text, speed, language, gender="female"):
        """Generate and send audio for a single sentence."""
        async for audio_bytes in tts_engine.generate_audio_stream(text, speed=speed, language=language, gender=gender):
            encoded = base64.b64encode(audio_bytes).decode()
            await websocket.send_json({"type": "audio", "data": encoded})

    async def fetch_word_bank(reply, lang, diff, token_mode="high"):
        if token_mode == "low":
            return # Skip word bank completely in low mode
        include_decoys = "Elementary" in diff
        words, ok = await ai_client.generate_word_bank(reply, lang, include_decoys, token_mode=token_mode)
        if ok and words:
            await websocket.send_json({"type": "word_bank", "words": words})

    async def fetch_grammar(user_text, lang, diff, scenario, token_mode="high"):
        if token_mode == "low":
            return # Skip grammar checks completely in low mode
        history_msgs = ai_client.scenario_history[-4:] if scenario else ai_client.conversation_history[-4:]
        history_str = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in history_msgs if m.get('role')])
        grammar, grammar_score, ok = await ai_client.analyze_grammar(user_text, lang, diff, context_history=history_str, token_mode=token_mode)
        print(f"[DEBUG] fetch_grammar output: '{grammar}' score={grammar_score}", flush=True)
        if ok and grammar:
            # Always record the real grammar score
            analytics_manager.add_grammar_score(grammar_score)
            if grammar.strip() != "PERFECT":
                analytics_manager.add_mistake()
                if scenario:
                    scenario_grammar_errors.append(grammar)
            await websocket.send_json({"type": "grammar", "content": grammar})

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[DEBUG] Received WebSocket data: {data}", flush=True)
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

            # --- Warmup TTS ---
            if msg_type == "warmup_tts":
                req_lang = payload.get("language", "Japanese")
                if req_lang == "None":
                    continue
                req_gender = payload.get("gender", "female")
                try:
                    await websocket.send_json({"type": "tts_warmup_start"})
                    await tts_engine.warmup(req_lang, req_gender)
                    await websocket.send_json({"type": "tts_warmup_done"})
                except Exception as e:
                    print(f"[ERROR] Warmup failed: {e}")
                    await websocket.send_json({"type": "tts_warmup_done"})
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
                token_mode = payload.get("token_mode", "high")
                await send_audio(reply, req_speed, language, req_gender)
                await websocket.send_json({"type": "audio_done"})
                
                enable_word_bank = payload.get("enable_word_bank", True)
                if enable_word_bank:
                    asyncio.create_task(fetch_word_bank(reply, language, difficulty, token_mode))
                continue

            # --- Normal / Scenario Chat ---
            user_text = payload.get("text", "")
            language = payload.get("language", "Japanese")
            difficulty = payload.get("difficulty", "Intermediate")
            scenario = payload.get("scenario")
            reading_mode = payload.get("reading_mode", "なし")
            req_speed = float(payload.get("speed", 1.0))
            enable_grammar = payload.get("enable_grammar", True)
            enable_grammar = payload.get("enable_grammar", True)
            enable_word_bank = payload.get("enable_word_bank", True)
            req_gender = payload.get("gender", "female")
            token_mode = payload.get("token_mode", "high")
            print(f"[DEBUG] Chat payload received: enable_grammar={enable_grammar}")

            # Track speaking analytics
            duration = payload.get("duration")
            db_user = db.query(User).filter(User.id == user_id).first()
            if db_user:
                if db_user.force_low_token_mode:
                    token_mode = "low"
                if db_user.forced_language:
                    language = db_user.forced_language
                if db_user.forced_difficulty:
                    difficulty = db_user.forced_difficulty
            
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
                generator = ai_client.get_scenario_reply_stream(user_text, language, difficulty, scenario_dict, enable_grammar, enable_word_bank, user_name=user_name, voice_gender=req_gender, token_mode=token_mode)
            else:
                # Fetch notebook words for topic steering
                notebook_words = []
                try:
                    vocab_entries = db.query(Vocabulary).filter(Vocabulary.user_id == user_id).order_by(Vocabulary.first_seen_at.desc()).limit(30).all()
                    notebook_words = [v.word for v in vocab_entries if v.word]
                except Exception:
                    pass
                generator = ai_client.get_reply_stream(user_text, language, difficulty, enable_grammar, enable_word_bank, user_name=user_name, notebook_words=notebook_words, voice_gender=req_gender, token_mode=token_mode)

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
                    if extras.get("tokens"):
                        await websocket.send_json({"type": "tokens", "content": extras["tokens"]})
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
                # Add messages to DB
                if user_text:
                    user_msg_db = Message(user_id=user_id, session_id=session_id, role="User", content=user_text)
                    db.add(user_msg_db)
                if final_full_reply:
                    ai_msg_db = Message(user_id=user_id, session_id=session_id, role="AI", content=final_full_reply)
                    db.add(ai_msg_db)
                db.commit()

                await websocket.send_json({"type": "audio_done"})

                if final_full_reply:
                    clean_reply = final_full_reply.replace("[GOAL_REACHED]", "").strip()
                    print(f"[DEBUG] Creating fetch tasks. enable_grammar={enable_grammar}", flush=True)
                    if enable_grammar:
                        asyncio.create_task(fetch_grammar(user_text, language, difficulty, scenario, token_mode))
                    if enable_word_bank:
                        asyncio.create_task(fetch_word_bank(clean_reply, language, difficulty, token_mode))

                if goal_reached or "[GOAL_REACHED]" in (final_full_reply or ""):
                    analytics_manager.add_fluency_score(random.randint(70, 95))
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
        # Generate summary
        try:
            messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp).all()
            if len(messages) > 0:
                text_to_summarize = "\n".join([f"{m.role}: {m.content}" for m in messages])
                prompt = f"Summarize the entirety of this conversation into 1 or more topics succinctly:\n{text_to_summarize}"
                summary = await ai_client._complete([{"role": "user", "content": prompt}], max_tokens=150)
                
                conv_session = db.query(ConversationSession).filter(ConversationSession.id == session_id).first()
                if conv_session:
                    conv_session.summary = summary
                    db.commit()
        except Exception as e:
            print(f"Error summarizing session: {e}", flush=True)
        finally:
            db.close()

# ---------- REST endpoints ----------

# --- Admin Endpoints ---

class GroupCreate(BaseModel):
    name: str
    admin_id: int

class UserGroupUpdate(BaseModel):
    group_id: int | None

class UserSettingsUpdate(BaseModel):
    force_low_token_mode: bool | None = None
    forced_language: str | None = None
    forced_difficulty: str | None = None
    forced_reading_mode: str | None = None

@app.post("/api/admin/groups")
def create_group(req: GroupCreate, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == req.admin_id, User.is_admin == True).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    new_group = Group(name=req.name, admin_id=admin.id)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return {"id": new_group.id, "name": new_group.name}

@app.get("/api/admin/my-groups")
def get_my_groups(admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin: raise HTTPException(status_code=403, detail="Not an admin")
    groups = db.query(Group).filter(Group.admin_id == admin_id).all()
    
    group_list = []
    for group in groups:
        users = db.query(User).filter(User.group_id == group.id).all()
        user_data = []
        for u in users:
            user_data.append({
                "id": u.id,
                "username": u.username,
                "force_low_token_mode": u.force_low_token_mode,
                "forced_language": u.forced_language,
                "forced_difficulty": u.forced_difficulty,
                "forced_reading_mode": u.forced_reading_mode,
                "total_speaking_time": u.total_seconds_spoken
            })
        group_list.append({"group": {"id": group.id, "name": group.name}, "users": user_data})
    return {"groups": group_list}

@app.delete("/api/admin/groups/{group_id}")
def delete_group(group_id: int, admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin: raise HTTPException(status_code=403, detail="Not an admin")
    group = db.query(Group).filter(Group.id == group_id, Group.admin_id == admin_id).first()
    if not group: raise HTTPException(status_code=404, detail="Group not found")
    
    users = db.query(User).filter(User.group_id == group.id).all()
    for u in users:
        u.group_id = None
        
    db.query(GroupInvite).filter(GroupInvite.group_id == group.id).delete()
        
    db.delete(group)
    db.commit()
    return {"success": True}

@app.get("/api/users/{user_id}/overrides")
def get_user_overrides(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: return {}
    return {
        "force_low_token_mode": user.force_low_token_mode,
        "forced_language": user.forced_language,
        "forced_difficulty": user.forced_difficulty,
        "forced_reading_mode": user.forced_reading_mode
    }

@app.get("/api/admin/groups/{group_id}")
def get_group(group_id: int, admin_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id, Group.admin_id == admin_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    users = db.query(User).filter(User.group_id == group_id).all()
    user_data = []
    for u in users:
        user_data.append({
            "id": u.id,
            "username": u.username,
            "force_low_token_mode": u.force_low_token_mode,
            "forced_language": u.forced_language,
            "forced_difficulty": u.forced_difficulty,
            "total_speaking_time": u.total_seconds_spoken
        })
    return {"group": group.name, "users": user_data}

@app.put("/api/admin/users/{target_user_id}/group")
def assign_user_to_group(target_user_id: int, req: UserGroupUpdate, admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    if req.group_id is not None:
        group = db.query(Group).filter(Group.id == req.group_id, Group.admin_id == admin_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found or not owned by admin")
    
    user = db.query(User).filter(User.id == target_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.group_id = req.group_id
    db.commit()
    return {"success": True}

class InviteRequest(BaseModel):
    username: str

@app.post("/api/admin/groups/{group_id}/invite")
def invite_user_to_group(group_id: int, req: InviteRequest, admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin: raise HTTPException(status_code=403, detail="Not an admin")
    group = db.query(Group).filter(Group.id == group_id, Group.admin_id == admin_id).first()
    if not group: raise HTTPException(status_code=404, detail="Group not found or not owned by admin")
    user = db.query(User).filter(User.username == req.username).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    
    existing = db.query(GroupInvite).filter(GroupInvite.group_id == group_id, GroupInvite.user_id == user.id, GroupInvite.status == "pending").first()
    if existing: return {"success": True, "message": "Invite already pending"}
    
    invite = GroupInvite(group_id=group_id, user_id=user.id)
    db.add(invite)
    db.commit()
    return {"success": True, "message": f"Invite sent to {user.username}!"}

class InviteAction(BaseModel):
    action: str

@app.get("/api/users/{user_id}/invites")
def get_user_invites(user_id: int, db: Session = Depends(get_db)):
    invites = db.query(GroupInvite).filter(GroupInvite.user_id == user_id, GroupInvite.status == "pending").all()
    return [{"id": i.id, "group_name": i.group.name, "admin_name": i.group.admin.username} for i in invites]

@app.post("/api/users/{user_id}/invites/{invite_id}")
def handle_invite(user_id: int, invite_id: int, req: InviteAction, db: Session = Depends(get_db)):
    invite = db.query(GroupInvite).filter(GroupInvite.id == invite_id, GroupInvite.user_id == user_id).first()
    if not invite or invite.status != "pending":
        raise HTTPException(status_code=404, detail="Invite not found or already processed")
        
    if req.action == "accept":
        invite.status = "accepted"
        user = db.query(User).filter(User.id == user_id).first()
        user.group_id = invite.group_id
    else:
        invite.status = "declined"
        
    db.commit()
    return {"success": True}

@app.put("/api/admin/users/{target_user_id}/settings")
def update_user_settings(target_user_id: int, req: UserSettingsUpdate, admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    user = db.query(User).filter(User.id == target_user_id).first()
    if not user or (user.group and user.group.admin_id != admin_id):
        raise HTTPException(status_code=404, detail="User not found in your group")
    
    update_data = req.model_dump(exclude_unset=True) if hasattr(req, "model_dump") else req.dict(exclude_unset=True)
    if "force_low_token_mode" in update_data:
        user.force_low_token_mode = update_data["force_low_token_mode"]
    if "forced_language" in update_data:
        user.forced_language = update_data["forced_language"]
    if "forced_difficulty" in update_data:
        user.forced_difficulty = update_data["forced_difficulty"]
    if "forced_reading_mode" in update_data:
        user.forced_reading_mode = update_data["forced_reading_mode"]
    db.commit()
    return {"success": True}

@app.get("/api/admin/sessions/{target_user_id}")
def get_user_sessions(target_user_id: int, admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    user = db.query(User).filter(User.id == target_user_id).first()
    if not user or (user.group and user.group.admin_id != admin_id):
        raise HTTPException(status_code=404, detail="User not found in your group")
    
    sessions = db.query(ConversationSession).filter(ConversationSession.user_id == target_user_id).order_by(ConversationSession.start_time.desc()).all()
    return [{"id": s.id, "start_time": s.start_time.isoformat(), "summary": s.summary} for s in sessions]

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
async def transcribe_audio(file: UploadFile = File(...), language: str = Form("Japanese"), user_id: int = Form(0)):
    from stt_engine import STTEngine
    stt = STTEngine()
    audio_bytes = await file.read()
    
    lang_map = {
        "Japanese": "ja-JP",
        "Korean": "ko-KR",
        "Chinese": "zh-CN",
        "Spanish": "es-ES",
        "French": "fr-FR",
        "Italian": "it-IT",
        "English": "en-US"
    }
    bcp47_lang = lang_map.get(language, "ja-JP")
    
    text, _ = stt.transcribe_audio(audio_bytes, target_language=bcp47_lang)
    
    if text.startswith("ERROR:") or not text:
        return {"text": text, "pronunciation": {"overall_score": 0, "phonemes": []}}
        
    base_score = 80
    if stt.last_audio is not None:
        try:
            from tts_engine import TTSEngine
            from audio_comparison import compare_audio
            tts_engine = TTSEngine()
            
            tts_wav_bytes = bytearray()
            async for chunk in tts_engine.generate_audio_stream(text, speed=1.0, language=language, gender="female"):
                tts_wav_bytes.extend(chunk)
                
            if tts_wav_bytes:
                base_score = compare_audio(stt.last_audio, stt.sample_rate, bytes(tts_wav_bytes))
        except Exception as e:
            print(f"Audio comparison error: {e}")

    phonemes = []
    for char in text:
        if char.strip():
            score = max(0, min(100, base_score + random.randint(-5, 5)))
            phonemes.append({"char": char, "score": score})
        else:
            phonemes.append({"char": char, "score": 100})
            
    pronunciation = {
        "overall_score": base_score,
        "phonemes": phonemes
    }
    
    # Save pronunciation score to analytics
    if user_id > 0 and base_score > 0:
        try:
            from analytics import AnalyticsManager
            pron_db = SessionLocal()
            pron_analytics = AnalyticsManager(pron_db, user_id)
            pron_analytics.add_pronunciation_score(base_score)
            pron_db.close()
        except Exception as e:
            print(f"Failed to save pronunciation score: {e}")

    return {"text": text, "pronunciation": pronunciation}

@app.get("/api/notebook")
async def get_notebook(user_id: int):
    db = SessionLocal()
    try:
        vocab = db.query(Vocabulary).filter(Vocabulary.user_id == user_id).order_by(Vocabulary.first_seen_at.desc()).all()
        return [{"id": v.id, "word": v.word, "definition": v.definition, "next_review": v.next_review_date.isoformat() if v.next_review_date else None} for v in vocab]
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
        return {"id": new_vocab.id, "word": new_vocab.word, "definition": new_vocab.definition}
    finally:
        db.close()

@app.get("/api/notebook/review")
async def get_review_items(user_id: int):
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        items = db.query(Vocabulary).filter(
            Vocabulary.user_id == user_id,
            Vocabulary.next_review_date <= now
        ).all()
        return [{"id": v.id, "word": v.word, "definition": v.definition} for v in items]
    finally:
        db.close()

@app.post("/api/notebook/review/{vocab_id}")
async def review_vocab(vocab_id: int, payload: dict):
    quality = payload.get("quality", 0) # 0-5
    db = SessionLocal()
    try:
        v = db.query(Vocabulary).filter(Vocabulary.id == vocab_id).first()
        if not v:
            return {"error": "Not found"}
        
        # SuperMemo-2
        if quality >= 3:
            if v.repetitions == 0:
                v.interval = 1
            elif v.repetitions == 1:
                v.interval = 6
            else:
                v.interval = int(round(v.interval * v.ease_factor))
            v.repetitions += 1
        else:
            v.repetitions = 0
            v.interval = 1
            
        v.ease_factor = v.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if v.ease_factor < 1.3:
            v.ease_factor = 1.3
            
        v.next_review_date = datetime.utcnow() + timedelta(days=v.interval)
        db.commit()
        return {"success": True, "next_review": v.next_review_date.isoformat()}
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