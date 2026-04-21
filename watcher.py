import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
import os
from settings import get_settings

# Set the path to the folder you want to observe
WATCHED_DIR = str(get_settings().watch_path) if get_settings().watch_path else ""

class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        # Trigger content generation and posting for any file in the folder
        print(f"Change detected in {event.src_path}, generating post...")
        # Example: call your FastAPI endpoint
        try:
            prompt = f"Change detected in {event.src_path}"
            # Generate content
            gen_resp = requests.post("http://127.0.0.1:8000/generate-content/", json={"prompt": prompt})
            content = gen_resp.json().get("responses", "")
            # Post content (to Twitter as example)
            post_resp = requests.post("http://127.0.0.1:8000/post-content/", json={
                "platform": "twitter",
                "content": str(content)
            })
            print("Post response:", post_resp.json())
        except Exception as e:
            print("Error posting content:", e)

if __name__ == "__main__":
    if not WATCHED_DIR or not os.path.exists(WATCHED_DIR):
        raise SystemExit(
            "WATCH_PATH is not set or does not exist. Set WATCH_PATH in your environment or .env."
        )
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=True)
    observer.start()
    print(f"Watching directory: {WATCHED_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
