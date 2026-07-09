import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey, Text, Date, text, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship


# Database URL configuration
DB_USER = os.getenv("POSTGRES_USER", "polyglot")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "polyglot_secret")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "polyglot")

DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    admin = relationship("User", foreign_keys=[admin_id])
    users = relationship("User", back_populates="group", foreign_keys="[User.group_id]")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    nickname = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    avg_chars_per_second = Column(Float, default=5.0)
    total_chars_spoken = Column(Integer, default=0)
    total_seconds_spoken = Column(Float, default=0.0)
    avatar = Column(Text, nullable=True)
    
    # B2B Admin fields
    is_admin = Column(Boolean, default=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    force_low_token_mode = Column(Boolean, default=False)
    forced_language = Column(String(50), nullable=True)
    forced_difficulty = Column(String(50), nullable=True)
    forced_reading_mode = Column(String(50), nullable=True)
    
    group = relationship("Group", back_populates="users", foreign_keys=[group_id])
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    vocabularies = relationship("Vocabulary", back_populates="user", cascade="all, delete-orphan")
    analytics = relationship("Analytic", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("ConversationSession", back_populates="user", cascade="all, delete-orphan")
    invites = relationship("GroupInvite", back_populates="user", cascade="all, delete-orphan")
    weak_points = relationship("WeakPoint", back_populates="user", cascade="all, delete-orphan")

class GroupInvite(Base):
    __tablename__ = "group_invites"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    group = relationship("Group")
    user = relationship("User", back_populates="invites")

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    
    id = Column(String(100), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(100), ForeignKey("conversation_sessions.id"), nullable=True)
    role = Column(String(20), nullable=False) # 'User', 'AI', 'System'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="messages")
    session = relationship("ConversationSession", back_populates="messages")

class Vocabulary(Base):
    __tablename__ = "vocabularies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word = Column(String(100), nullable=False)
    definition = Column(Text, nullable=False)
    language = Column(String(50))
    times_referenced = Column(Integer, default=1)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    
    # SRS Fields
    next_review_date = Column(DateTime, default=datetime.utcnow)
    interval = Column(Integer, default=0)
    ease_factor = Column(Float, default=2.5)
    repetitions = Column(Integer, default=0)
    
    user = relationship("User", back_populates="vocabularies")

class Analytic(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    
    total_speaking_time = Column(Float, default=0.0)
    mistakes_count = Column(Integer, default=0)
    
    # Track accumulated values for averaging later
    sum_fluency_score = Column(Float, default=0.0)
    count_fluency_score = Column(Integer, default=0)
    
    sum_grammar_score = Column(Float, default=0.0)
    count_grammar_score = Column(Integer, default=0)
    
    sum_listening_score = Column(Float, default=0.0)
    count_listening_score = Column(Integer, default=0)
    
    sum_pronunciation_score = Column(Float, default=0.0)
    count_pronunciation_score = Column(Integer, default=0)

    # Fluency sub-stats (fluency = average of confidence, flow, grammar)
    sum_confidence_score = Column(Float, default=0.0)
    count_confidence_score = Column(Integer, default=0)

    sum_flow_score = Column(Float, default=0.0)
    count_flow_score = Column(Integer, default=0)

    user = relationship("User", back_populates="analytics")


class WeakPoint(Base):
    """Aggregated counter of things a user struggles with, so the dashboard can
    surface weak points without storing a row per occurrence (light load).

    category: 'grammar' | 'flow' | 'confidence'
    key:      the grammar issue, or the word/sound where flow/confidence dropped
    """
    __tablename__ = "weak_points"
    __table_args__ = (UniqueConstraint("user_id", "category", "key", name="uq_weakpoint"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(20), nullable=False)
    key = Column(String(200), nullable=False)
    count = Column(Integer, default=1)
    sum_score = Column(Float, default=0.0)   # accumulated severity score, for averaging
    last_seen = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="weak_points")

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Existing migrations
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar TEXT;"))
    except Exception:
        pass
        
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN nickname VARCHAR(50);"))
    except Exception:
        pass

    # New B2B Admin migrations
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN group_id INTEGER REFERENCES groups(id);"))
            conn.execute(text("ALTER TABLE users ADD COLUMN force_low_token_mode BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN forced_language VARCHAR(50);"))
            conn.execute(text("ALTER TABLE users ADD COLUMN forced_difficulty VARCHAR(50);"))
    except Exception:
        pass
        
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE messages ADD COLUMN session_id VARCHAR(100) REFERENCES conversation_sessions(id);"))
    except Exception:
        pass

    # SRS migrations
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE vocabularies ADD COLUMN next_review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE vocabularies ADD COLUMN interval INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE vocabularies ADD COLUMN ease_factor FLOAT DEFAULT 2.5;"))
            conn.execute(text("ALTER TABLE vocabularies ADD COLUMN repetitions INTEGER DEFAULT 0;"))
    except Exception:
        pass

    # Pronunciation analytics migration
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE analytics ADD COLUMN sum_pronunciation_score FLOAT DEFAULT 0.0;"))
            conn.execute(text("ALTER TABLE analytics ADD COLUMN count_pronunciation_score INTEGER DEFAULT 0;"))
    except Exception:
        pass

    # Fluency sub-stats migration (confidence + flow)
    for col, coltype in [
        ("sum_confidence_score", "FLOAT DEFAULT 0.0"),
        ("count_confidence_score", "INTEGER DEFAULT 0"),
        ("sum_flow_score", "FLOAT DEFAULT 0.0"),
        ("count_flow_score", "INTEGER DEFAULT 0"),
    ]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE analytics ADD COLUMN {col} {coltype};"))
        except Exception:
            pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
