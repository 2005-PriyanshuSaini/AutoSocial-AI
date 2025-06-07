import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime

# Load database URL from environment variable (Neon Postgres)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# For Neon, use sslmode=require in the URL if not already present
if "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

# Create database engine
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)  # Set echo=True for debugging

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# --- Models ---
class GeneratedPost(Base):
    __tablename__ = "generated_posts"
    id = Column(Integer, primary_key=True, index=True)
    file = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected, posted
    platform = Column(String, nullable=True)    # Set when posted

class SessionSummaryPost(Base):
    __tablename__ = "session_summary_posts"
    id = Column(Integer, primary_key=True, index=True)
    summary = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, approved, posted
    platform = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())

class WatchSessionLog(Base):
    __tablename__ = "watch_session_logs"
    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime, nullable=True)
    path = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    result_summary = Column(Text, nullable=True)

class FileChangeLog(Base):
    __tablename__ = "file_change_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    diff_summary = Column(Text, nullable=True)
    ai_results = Column(Text, nullable=True)  # Store as JSON string

# --- DB Utility Functions ---

def create_all_tables():
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()

# CRUD for GeneratedPost
def add_generated_post(file, content, status="pending", platform=None):
    db = get_session()
    post = GeneratedPost(file=file, content=content, status=status, platform=platform)
    db.add(post)
    db.commit()
    db.refresh(post)
    db.close()
    return post

def update_generated_post_content(post_id, new_content):
    db = get_session()
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if post:
        post.content = new_content
        db.commit()
        db.refresh(post)
    db.close()
    return post

def set_generated_post_status(post_id, status):
    db = get_session()
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if post:
        post.status = status
        db.commit()
        db.refresh(post)
    db.close()
    return post

def list_generated_posts():
    db = get_session()
    posts = db.query(GeneratedPost).all()
    result = [
        {
            "id": p.id,
            "file": p.file,
            "content": str(p.content),
            "status": p.status,
            "platform": p.platform,
            "type": "custom" if p.file == "custom" else "ai"
        }
        for p in posts
    ]
    db.close()
    return result

# CRUD for SessionSummaryPost
def add_session_summary_post(summary, status="pending", platform=None):
    db = get_session()
    post = SessionSummaryPost(summary=summary, status=status, platform=platform)
    db.add(post)
    db.commit()
    db.refresh(post)
    db.close()
    return post

# CRUD for WatchSessionLog
def add_watch_session_log(path, duration_minutes):
    db = get_session()
    session_log = WatchSessionLog(
        started_at=datetime.now(),
        path=path,
        duration_minutes=duration_minutes
    )
    db.add(session_log)
    db.commit()
    db.refresh(session_log)
    db.close()
    return session_log

def update_watch_session_log(session_id, ended_at, result_summary):
    db = get_session()
    session_log = db.query(WatchSessionLog).filter(WatchSessionLog.id == session_id).first()
    if session_log:
        session_log.ended_at = ended_at
        session_log.result_summary = result_summary
        db.commit()
    db.close()

# CRUD for FileChangeLog
def add_file_change_log(session_id, file_path, diff_summary, ai_results):
    db = get_session()
    file_log = FileChangeLog(
        session_id=session_id,
        file_path=file_path,
        diff_summary=diff_summary,
        ai_results=ai_results
    )
    db.add(file_log)
    db.commit()
    db.close()
    return file_log