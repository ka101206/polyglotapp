import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey, Text, Date, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from pgvector.sqlalchemy import Vector

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

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    avg_chars_per_second = Column(Float, default=5.0)
    total_chars_spoken = Column(Integer, default=0)
    total_seconds_spoken = Column(Float, default=0.0)
    
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    vocabularies = relationship("Vocabulary", back_populates="user", cascade="all, delete-orphan")
    analytics = relationship("Analytic", back_populates="user", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False) # 'User', 'AI', 'System'
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384)) # all-MiniLM-L6-v2 uses 384 dimensions
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="messages")

class Vocabulary(Base):
    __tablename__ = "vocabularies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word = Column(String(100), nullable=False)
    definition = Column(Text, nullable=False)
    language = Column(String(50))
    times_referenced = Column(Integer, default=1)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    
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
    
    user = relationship("User", back_populates="analytics")

def init_db():
    # Attempt to create pgvector extension if it doesn't exist
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
