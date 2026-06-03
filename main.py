import os
import bcrypt
from fastapi import FastAPI, Depends, HTTPException, WebSocket, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from database import init_db, get_db, User, Message, Vocabulary
from analytics import AnalyticsManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pydantic import BaseModel

class AuthRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    user_id: int
    username: str
    message: str

@app.post("/auth/register", response_model=AuthResponse)
def register(req: AuthRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(username=req.username, password_hash=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"user_id": new_user.id, "username": new_user.username, "message": "Registered successfully"}

@app.post("/auth/login", response_model=AuthResponse)
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not bcrypt.checkpw(req.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"user_id": user.id, "username": user.username, "message": "Logged in successfully"}

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

from fastapi import WebSocketDisconnect
from ai_client import AIClient
from tts_engine import TTSEngine
import json
import base64

ai_client_instance = AIClient()
tts_engine_instance = TTSEngine()

@app.websocket("/ws/chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    # In a real app, you'd fetch the user's conversation history from DB here
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_text = payload.get("text", "")
            
            # 1. Get AI Reply
            reply, success = ai_client_instance.get_reply(user_text)
            
            if success:
                # Send text back to UI immediately
                await websocket.send_json({"type": "text", "content": reply})
                
                # 2. Generate and stream audio
                # For this prototype we assume Japanese TTS
                for chunk_bytes in tts_engine_instance.generate_audio_stream(reply):
                    # We encode raw WAV bytes to base64 to send over JSON WebSocket
                    encoded = base64.b64encode(chunk_bytes).decode('utf-8')
                    await websocket.send_json({"type": "audio", "data": encoded})
                    
                await websocket.send_json({"type": "audio_done"})
            else:
                await websocket.send_json({"type": "error", "content": reply})
                
    except WebSocketDisconnect:
        print(f"Client {user_id} disconnected")

@app.post("/api/audio/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    from stt_engine import STTEngine
    stt = STTEngine()
    audio_bytes = await file.read()
    text = stt.transcribe_audio(audio_bytes)
    return {"text": text}