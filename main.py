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
from ai import ask_hf_api
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from db import SessionLocal, Base, engine
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker
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

# SQLAlchemy model for generated posts
class GeneratedPost(Base):
    __tablename__ = "generated_posts"
    id = Column(Integer, primary_key=True, index=True)
    file = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected, posted
    platform = Column(String, nullable=True)    # Set when posted

# Add a new SQLAlchemy model for session summary posts if not already present
class SessionSummaryPost(Base):
    __tablename__ = "session_summary_posts"
    id = Column(Integer, primary_key=True, index=True)
    summary = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, approved, posted
    platform = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())

# Create tables if not exist
Base.metadata.create_all(bind=engine)

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
    Start a watch session for a given folder and duration (in minutes).
    """
    data = await request.json()
    path = data.get("path")
    duration = data.get("duration")  # in minutes
    if not path or not os.path.exists(path):
        return JSONResponse({"error": "Invalid path"}, status_code=400)
    try:
        duration = int(duration)
        if duration <= 0:
            raise ValueError()
    except Exception:
        return JSONResponse({"error": "Invalid duration"}, status_code=400)
    if watch_session["active"]:
        return JSONResponse({"error": "A session is already active."}, status_code=400)
    stop_event = threading.Event()
    watch_session.update({
        "active": True,
        "changed_files": set(),
        "thread": None,
        "stop_event": stop_event,
        "path": path,
        "end_time": datetime.now() + timedelta(minutes=duration),
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
    def session_watcher():
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
                if datetime.now() >= watch_session["end_time"]:
                    break
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()
            changed_files = list(watch_session["changed_files"])
            results = {}
            diff_summaries = {}
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
                    responses = gen_resp.json().get("responses", {})
                    results[file_path] = responses
                    # Save each model's content as a separate DB row
                    db = SessionLocal()
                    for model_name, content in responses.items():
                        db_post = GeneratedPost(
                            file=f"{file_path} [{model_name}]",
                            content=str(content),
                            status="pending"
                        )
                        db.add(db_post)
                    db.commit()
                    db.close()
                except Exception as e:
                    results[file_path] = f"Error: {e}"
            # --- Session-level summary ---
            session_summary = generate_session_summary(diff_summaries)
            watch_session["results"] = {"file_summaries": results, "session_summary": session_summary}
            watch_session["active"] = False
    t = threading.Thread(target=session_watcher, daemon=True)
    watch_session["thread"] = t
    t.start()
    return {"message": f"Started watching {path} for {duration} minutes."}

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

@app.get("/generated-posts/")
def list_generated_posts():
    db = SessionLocal()
    posts = db.query(GeneratedPost).all()
    result = [
        {
            "id": p.id,
            "file": p.file,
            "content": str(p.content),  # Ensure content is always a string
            "status": p.status,
            "platform": p.platform,
            "type": "custom" if p.file == "custom" else "ai"
        }
        for p in posts
    ]
    db.close()
    return result

@app.post("/test-huggingface/")
def test_huggingface(request: GenerateRequest) -> Dict[str, str]:
    """
    Test Hugging Face API content generation only.
    """
    prompt = request.prompt or DEFAULT_PROMPT
    result = ask_hf_api(prompt)
    return {"prompt": prompt, "huggingface_result": result}

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
    if now.day == 1 and now.hour == 0:  # Only run at midnight on the 1st
        db = SessionLocal()
        # Compose a monthly summary prompt (customize as needed)
        prompt = (
            "It's the start of a new month! Write a professional, engaging summary post for our project's progress and plans for this month, suitable for both Twitter and LinkedIn."
        )
        summary = query_all_models(prompt)
        # Store as a session summary post
        post = SessionSummaryPost(summary=str(summary), status="approved", platform="both")
        db.add(post)
        db.commit()
        db.refresh(post)
        # Post to both platforms
        post_to_x(str(summary))
        post_to_linkedin(str(summary))
        db.close()