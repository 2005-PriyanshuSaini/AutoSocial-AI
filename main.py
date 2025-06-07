import os
import time
import random
import requests
import threading
import difflib
from pathlib import Path
from fastapi import FastAPI, Request, BackgroundTasks, Body, Query
from pydantic import BaseModel
from typing import Dict, List, Any
from ai import askall_models as query_all_models
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from db import (
    GeneratedPost,
    SessionSummaryPost,
    WatchSessionLog,
    FileChangeLog,
    create_all_tables,
    add_generated_post,
    update_generated_post_content,
    set_generated_post_status,
    list_generated_posts,
    add_session_summary_post,
    add_watch_session_log,
    update_watch_session_log,
    add_file_change_log,
    SessionLocal,
    Base,
    engine,
)
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from social import fetch_x_trending_topics, fetch_linkedin_trending_topics, post_to_x, post_to_linkedin
from datetime import datetime, timedelta
from prompt_templates import DEFAULT_PROMPT
from fastapi_utils.tasks import repeat_every

# Store session state for watch session (move this to the top)
watch_session = {
    "active": False,
    "changed_files": set(),
    "thread": None,
    "stop_event": None,
    "path": None,
    "end_time": None,
    "results": None
}

app = FastAPI()

# Mount static directory for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    # Serve index.html using absolute path to avoid working directory issues
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(index_path)

class ReviewRequest(BaseModel):
    post_id: int
    status: str  # "approved" or "rejected"

class PostRequest(BaseModel):
    post_id: int
    platform: Any  # Accept str or list
    content: str
    urn_type: str = None  # "author", "organization", or None

class GenerateRequest(BaseModel):
    prompt: str

class CustomContentRequest(BaseModel):
    file: str = "custom"
    content: str

class EditContentRequest(BaseModel):
    post_id: int
    new_content: str

# Remove all SQLAlchemy model class definitions from main.py
# Instead, import them from db.py

from db import (
    GeneratedPost,
    SessionSummaryPost,
    WatchSessionLog,
    FileChangeLog,
    create_all_tables,
    add_generated_post,
    update_generated_post_content,
    set_generated_post_status,
    list_generated_posts,
    add_session_summary_post,
    add_watch_session_log,
    update_watch_session_log,
    add_file_change_log,
    SessionLocal,
    Base,
    engine,
)

# Create tables if not exist
create_all_tables()

# Track generation stats and cancellation
generation_count = 0
generation_cancel_event = threading.Event()

@app.post("/generate-content/")
def generate_content(request: GenerateRequest) -> Dict[str, Any]:
    """
    Generate content using all models and return each response with its model name.
    """
    global generation_count
    if generation_cancel_event.is_set():
        return {"error": "Generation cancelled."}
    generation_count += 1
    prompt = request.prompt or DEFAULT_PROMPT
    responses = query_all_models(prompt)
    # Return each model's content with its name
    return {"prompt": prompt, "model_responses": responses}

@app.post("/save-generated-content/")
def save_generated_content(model: str = Query(...), content: str = Query(...)):
    """
    Save selected generated content as a pending post and return its ID.
    """
    db = SessionLocal()
    db_post = GeneratedPost(file=model, content=content, status="pending")
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    post_id = db_post.id
    db.close()
    return {"message": f"Content saved for approval. Use Post ID {post_id} to approve and post.", "id": post_id}

@app.post("/edit-generated-content/")
def edit_generated_content(request: EditContentRequest):
    """
    Edit the content of a generated post before approval/posting.
    """
    db = SessionLocal()
    post = db.query(GeneratedPost).filter(GeneratedPost.id == request.post_id).first()
    if not post:
        db.close()
        return {"error": "Post not found."}
    post.content = request.new_content
    db.commit()
    db.refresh(post)
    db.close()
    return {"message": f"Post {request.post_id} content updated."}

@app.post("/review-content/")
def review_content(request: ReviewRequest):
    db = SessionLocal()
    post = db.query(GeneratedPost).filter(GeneratedPost.id == request.post_id).first()
    if not post:
        db.close()
        return {"error": "Post not found."}
    if request.status not in ["approved", "rejected"]:
        db.close()
        return {"error": "Invalid status. Use 'approved' or 'rejected'."}
    post.status = request.status
    db.commit()
    db.refresh(post)
    db.close()
    return {"message": f"Post {request.post_id} marked as {request.status}.", "status": request.status}

@app.get("/trending-topics/")
def get_trending_topics() -> Dict[str, List[str]]:
    x_topics = fetch_x_trending_topics()
    linkedin_topics = fetch_linkedin_trending_topics()
    return {
        "x_trending_topics": x_topics,
        "linkedin_trending_topics": linkedin_topics
    }

@app.post("/post-content/")
def post_content(request: PostRequest):
    db = SessionLocal()
    post = db.query(GeneratedPost).filter(GeneratedPost.id == request.post_id).first()
    if not post:
        db.close()
        return {"error": "Post not found."}
    if post.status != "approved":
        db.close()
        return {"error": "Post must be approved before publishing."}
    post.status = "posted"
    # Support posting to multiple platforms
    platforms = request.platform if isinstance(request.platform, list) else [request.platform]
    results = {}
    for platform in platforms:
        post.platform = platform
        db.commit()
        db.refresh(post)
        if platform == "twitter":
            results["twitter"] = post_to_x(post.content)
        elif platform == "linkedin":
            results["linkedin"] = post_to_linkedin(post.content, urn_type=request.urn_type)
        else:
            results[platform] = {"error": "Unsupported platform"}
    db.close()
    return {"message": f"Post published to {', '.join(platforms)}: {post.content}", "result": results}

@app.post("/submit-custom-content/")
def submit_custom_content(request: CustomContentRequest):
    """
    Save custom content as a pending post and return its ID.
    """
    db = SessionLocal()
    db_post = GeneratedPost(file=request.file, content=request.content, status="pending")
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    db.close()
    return {"message": "Custom content submitted for approval.", "id": db_post.id}

# --- Watchdog automation logic ---

WATCHED_PATH = r"D:\Code-Base\DSA\c++"  # Default path
watcher_observer = None
watcher_thread = None
watcher_stop_event = threading.Event()
DEFAULT_IGNORE_FILE = os.path.join(os.path.dirname(__file__), "default_ignore.txt")

def load_gitignore_patterns(gitignore_path):
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    elif os.path.exists(DEFAULT_IGNORE_FILE):
        with open(DEFAULT_IGNORE_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    return patterns

def is_ignored(path, patterns):
    from fnmatch import fnmatch
    # Ensure path is relative to the watched directory and uses forward slashes
    rel_path = Path(path).resolve().relative_to(Path(WATCHED_PATH).resolve())
    rel_path_str = str(rel_path).replace("\\", "/")
    for pattern in patterns:
        # Normalize pattern to use forward slashes
        pattern = pattern.replace("\\", "/")
        # Handle folder ignore (trailing slash)
        if pattern.endswith("/"):
            if rel_path_str.startswith(pattern.rstrip("/")):
                return True
        # Handle file pattern
        if fnmatch(rel_path_str, pattern):
            return True
    return False

def start_watcher(path, stop_event):
    global watcher_observer
    GITIGNORE_PATH = os.path.join(path, ".gitignore") if os.path.isdir(path) else os.path.join(os.path.dirname(path), ".gitignore")
    GITIGNORE_PATTERNS = load_gitignore_patterns(GITIGNORE_PATH)

    class ChangeHandler(FileSystemEventHandler):
        def on_any_event(self, event):
            if event.is_directory:
                return
            if is_ignored(event.src_path, GITIGNORE_PATTERNS):
                return
            # --- FIX: Only generate content if not in a watch session ---
            if watch_session.get("active"):
                # Only record the file as changed, do not generate content here
                watch_session["changed_files"].add(os.path.abspath(event.src_path))
                return
            msg = f"Change detected in {event.src_path}, generating content..."
            print(msg)
            try:
                prompt = f"Change detected in {event.src_path}"
                gen_resp = requests.post("http://127.0.0.1:8000/generate-content/", json={"prompt": prompt})
                content = gen_resp.json().get("responses", "")
                db = SessionLocal()
                db_post = GeneratedPost(file=event.src_path, content=str(content), status="pending")
                db.add(db_post)
                db.commit()
                db.refresh(db_post)
                print(f"Generated content stored for approval (id={db_post.id})")
                db.close()
            except Exception as e:
                err_msg = f"Error generating content: {e}"
                print(err_msg)

    if watcher_observer:
        watcher_observer.stop()
    observer = Observer()
    event_handler = ChangeHandler()
    if os.path.isdir(path):
        observer.schedule(event_handler, path, recursive=True)
        print(f"Watching directory: {path}")
    else:
        observer.schedule(event_handler, os.path.dirname(path), recursive=False)
        print(f"Watching file: {path}")
    observer.start()
    watcher_observer = observer
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except Exception as e:
        print(f"Watcher thread exception: {e}")
    finally:
        observer.stop()
        print("Watcher stopping...")
        # Do not call observer.join() here, let the thread exit

@app.post("/start-watch-session/")
async def start_watch_session(request: Request, background_tasks: BackgroundTasks):
    global watch_session, previous_file_contents
    """
    Start a watch session for a given folder and duration.
    Accepts duration and duration_unit ('minutes' or 'hours').
    """
    data = await request.json()
    path = data.get("path")
    duration = data.get("duration")  # numeric value
    duration_unit = data.get("duration_unit", "minutes")  # default to minutes if not provided

    if not path or not os.path.exists(path):
        return JSONResponse({"error": "Invalid path"}, status_code=400)
    try:
        duration = int(duration)
        if duration <= 0:
            raise ValueError()
    except Exception:
        return JSONResponse({"error": "Invalid duration"}, status_code=400)
    if duration_unit not in ("minutes", "hours"):
        return JSONResponse({"error": "Invalid duration_unit. Use 'minutes' or 'hours'."}, status_code=400)
    if watch_session["active"]:
        return JSONResponse({"error": "A session is already active."}, status_code=400)
    stop_event = threading.Event()
    # Calculate end_time based on unit
    if duration_unit == "hours":
        end_time = datetime.now() + timedelta(hours=duration)
        duration_minutes = duration * 60
    else:
        end_time = datetime.now() + timedelta(minutes=duration)
        duration_minutes = duration
    watch_session.update({
        "active": True,
        "changed_files": set(),
        "thread": None,
        "stop_event": stop_event,
        "path": path,
        "end_time": end_time,
        "results": None
    })
    # At session start, store current content of all files in the watched path
    previous_file_contents = {}
    for root, dirs, files in os.walk(path):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    previous_file_contents[fpath] = f.read()
            except Exception:
                continue

    # --- FIX: create session_log and pass session_log_id into the thread ---
    session_log = add_watch_session_log(path, duration_minutes)
    session_log_id = session_log.id

    def session_watcher(session_log_id=session_log_id):
        class SessionHandler(FileSystemEventHandler):
            def on_any_event(self, event):
                if event.is_directory:
                    return
                rel_path = os.path.relpath(event.src_path, path)
                watch_session["changed_files"].add(os.path.abspath(event.src_path))
        observer = Observer()
        handler = SessionHandler()
        observer.schedule(handler, path, recursive=True)
        observer.start()
        try:
            while not stop_event.is_set():
                # --- FIX: check time and stop session if over ---
                if datetime.now() >= watch_session["end_time"]:
                    stop_event.set()
                    break
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()
            changed_files = list(watch_session["changed_files"])
            results = {}
            diff_summaries = {}
            db = SessionLocal()
            for file_path in changed_files:
                try:
                    old_content = previous_file_contents.get(file_path, "")
                    with open(file_path, "r", encoding="utf-8") as f:
                        new_content = f.read()
                    diff_summary = summarize_file_change(file_path, old_content, new_content)
                    diff_summaries[file_path] = diff_summary
                    # Use SUMMARY_PROMPT_TEMPLATE for AI
                    from prompt_templates import SUMMARY_PROMPT_TEMPLATE
                    prompt = SUMMARY_PROMPT_TEMPLATE.format(diff_summary=diff_summary)
                    gen_resp = requests.post("http://127.0.0.1:8000/generate-content/", json={"prompt": prompt})
                    # --- FIX: use model_responses for new API, fallback to responses ---
                    resp_json = gen_resp.json()
                    responses = resp_json.get("model_responses") or resp_json.get("responses", {})
                    results[file_path] = responses
                    # Save each model's content as a separate DB row
                    for model_name, content in responses.items():
                        db_post = GeneratedPost(
                            file=f"{file_path} [{model_name}]",
                            content=str(content),
                            status="pending"
                        )
                        db.add(db_post)
                    # Save file change log
                    file_log = FileChangeLog(
                        session_id=session_log_id,
                        file_path=file_path,
                        diff_summary=diff_summary,
                        ai_results=str(responses)
                    )
                    db.add(file_log)
                    db.commit()
                except Exception as e:
                    results[file_path] = f"Error: {e}"
            # --- Session-level summary ---
            session_summary = generate_session_summary(diff_summaries)
            # Update session log with summary and end time
            session_log = db.query(WatchSessionLog).filter(WatchSessionLog.id == session_log_id).first()
            session_log.ended_at = datetime.now()
            session_log.result_summary = str(session_summary)
            db.commit()
            db.close()
            watch_session["results"] = {"file_summaries": results, "session_summary": session_summary}
            watch_session["active"] = False

    t = threading.Thread(target=session_watcher, daemon=True)
    watch_session["thread"] = t
    t.start()
    return {"message": f"Started watching {path} for {duration} {duration_unit}."}

@app.post("/stop-watch-session/")
def stop_watch_session():
    global watch_session
    """
    Stop the current watch session early.
    """
    if not watch_session["active"]:
        return {"message": "No active session."}
    watch_session["stop_event"].set()
    return {"message": "Session stopping."}

@app.get("/watch-session-status/")
def watch_session_status():
    global watch_session
    """
    Get the status of the current watch session.
    """
    if not watch_session["active"]:
        return {
            "active": False,
            "results": watch_session.get("results")
        }
    return {
        "active": True,
        "path": watch_session["path"],
        "end_time": watch_session["end_time"].isoformat(),
        "changed_files": list(watch_session["changed_files"])
    }

@app.get("/watch-session-results/")
def watch_session_results():
    """
    Return the results of the last completed watch session.
    """
    global watch_session
    if watch_session.get("results"):
        return watch_session["results"]
    return {"error": "No session results available."}

@app.get("/generated-posts/")
def list_generated_posts(include_all: bool = False):
    """
    List generated posts.
    By default, returns all posts. If include_all=false, returns only approved/posted.
    You can pass ?include_all=true to get all posts including pending/rejected.
    """
    db = SessionLocal()
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
        if include_all or p.status in ("approved", "posted")
    ]
    db.close()
    return result

# --- Add endpoints for other tables for admin/debugging ---

@app.get("/session-summary-posts/")
def list_session_summary_posts():
    db = SessionLocal()
    posts = db.query(SessionSummaryPost).all()
    result = [
        {
            "id": p.id,
            "summary": str(p.summary),
            "status": p.status,
            "platform": p.platform,
            "created_at": p.created_at
        }
        for p in posts
    ]
    db.close()
    return result

@app.get("/watch-session-logs/")
def list_watch_session_logs():
    db = SessionLocal()
    logs = db.query(WatchSessionLog).all()
    result = [
        {
            "id": l.id,
            "started_at": l.started_at.isoformat() if l.started_at else None,
            "ended_at": l.ended_at.isoformat() if l.ended_at else None,
            "path": l.path,
            "duration_minutes": l.duration_minutes,
            "result_summary": l.result_summary
        }
        for l in logs
    ]
    db.close()
    return result

@app.get("/file-change-logs/")
def list_file_change_logs():
    db = SessionLocal()
    logs = db.query(FileChangeLog).all()
    result = [
        {
            "id": l.id,
            "session_id": l.session_id,
            "file_path": l.file_path,
            "diff_summary": l.diff_summary,
            "ai_results": l.ai_results
        }
        for l in logs
    ]
    db.close()
    return result

def summarize_file_change(file_path, old_content, new_content):
    diff = difflib.unified_diff(
        old_content.splitlines(), new_content.splitlines(),
        fromfile='before', tofile='after', lineterm=''
    )
    diff_text = '\n'.join(diff)
    return diff_text

def generate_session_summary(changes):
    from prompt_templates import SUMMARY_PROMPT_TEMPLATE
    # Aggregate all diffs into one prompt
    all_diffs = ""
    for file, summary in changes.items():
        all_diffs += f"File: {file}\nChanges:\n{summary}\n\n"
    prompt = SUMMARY_PROMPT_TEMPLATE.format(diff_summary=all_diffs)
    # Use only one model or all, as you prefer
    return query_all_models(prompt)

@app.on_event("startup")
@repeat_every(seconds=60*60)  # Check every hour
def monthly_post_task() -> None:
    from prompt_templates import SUMMARY_PROMPT_TEMPLATE
    now = datetime.now()
    # --- FIX: Always run for testing/demo, or adjust condition for your needs ---
    # For production, keep: if now.day == 1 and now.hour == 0:
    # For demo/testing, run every startup:
    # Remove the if-condition below to always create a SessionSummaryPost on startup
    # if now.day == 1 and now.hour == 0:
    db = SessionLocal()
    prompt = (
        "It's the start of a new month! Write a professional, engaging summary post for our project's progress and plans for this month, suitable for both Twitter and LinkedIn."
    )
    summary = query_all_models(prompt)
    post = SessionSummaryPost(summary=str(summary), status="approved", platform="both")
    db.add(post)
    db.commit()
    db.refresh(post)
    # Post to both platforms (optional, comment out if not needed)
    # post_to_x(str(summary))
    # post_to_linkedin(str(summary))
    db.close()