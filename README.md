# AutoSocial AI

AutoSocial AI is a Python automation project that helps you create social media posts or blog content based on your local development work. It watches a folder (like your codebase), detects updates, and generates content that can be posted to platforms like Twitter (X), LinkedIn, or your personal website.

![AutoSocial AI Demo](static/images/Landing%20page.png)

---

## 👤 Author

**Priyanshu Saini**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin)](https://www.linkedin.com/in/priyanshu-saini-4b4a0a28a/)
[![Twitter](https://img.shields.io/badge/X-1DA1F2?style=flat&logo=twitter)](https://twitter.com/Dev_Priyanshu_1)
[![Linktree](https://img.shields.io/badge/Linktree-43e55b?style=flat&logo=linktree)](https://linktr.ee/Priyanshu_Saini2005)

📧 **Email:** [Priyanshusaini9991@gmail.com](mailto:Priyanshusaini9991@gmail.com)  
📄 [Resume (PDF)](https://docs.google.com/document/d/1_LnjZy7qLLiSqB8eeqibY--Ht0c948B17oVZr9wiS1c/edit?usp=sharing)

---

## 🚧 Project Status

This project is currently in completed.

---

## ✨ Features

- Monitors a folder for file changes  
- Generates text content using AI (multiple models: ChatGPT, Gemini, Llama)  
- Can create short posts (e.g. Twitter, LinkedIn) or long posts (e.g. blogs)  
- Can post to multiple platforms  
- Option to post instantly or on a schedule  
- Session-based summaries for grouped changes  
- Custom content submission and approval workflow

---

## ⚙️ How It Works

1. You give AutoSocial AI access to your project folder.  
2. It monitors file changes and detects updates.  
3. Based on the changes, it generates a post like:

   > Added login system using FastAPI + JWT. Working well! 🔐  
   > #FastAPI #Python #DevLog

4. It then posts this content to Twitter, LinkedIn, or your portfolio.

<!-- Replace the below with your actual workflow image -->
![Workflow Example](static/images/Prompt%20Gen.png)
![Workflow Example](static/images/Watch%20Results.png)
![Workflow Example](static/images/History1.png)
![Workflow Example](static/images/History2.png)

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/autosocial-ai.git
cd autosocial-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the backend server

```bash
uvicorn main:app --reload
```
  > Then open your browser and visit:
  > http://localhost:8000/

---

## 🐳 Docker (Production-ish)

### Start everything (FastAPI + Postgres + Redis)

```bash
docker compose up --build
```

Then open `http://localhost:8000/` and check health at `http://localhost:8000/healthz`.

Docker is the easiest way to guarantee the intended runtime (**Python 3.11+**) regardless of what your system Python is.

By default the container runs **Gunicorn + Uvicorn workers**. You can tune:

- **`WEB_CONCURRENCY`**: number of worker processes
- **`GUNICORN_TIMEOUT`**: request timeout seconds
- **`GUNICORN_GRACEFUL_TIMEOUT`**: graceful shutdown seconds

### Run forever (auto-restart)

- With Docker: services are configured with `restart: unless-stopped` in `docker-compose.yml`.
- On Linux without Docker: you can run via `systemd` (example below).

#### Example `systemd` unit (Linux)

Create `~/.config/systemd/user/autosocial.service`:

```ini
[Unit]
Description=AutoSocial AI (FastAPI background service)
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=%h/path/to/Auto-Social AI
EnvironmentFile=%h/path/to/Auto-Social AI/.env
ExecStart=%h/path/to/Auto-Social AI/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
```

Then:

```bash
systemctl --user daemon-reload
systemctl --user enable --now autosocial.service
journalctl --user -u autosocial.service -f
```

### Watching your project files

- By default, Compose mounts `./watched` into the container at `/watched`.
- To watch a real folder, change the `app.volumes` entry in `docker-compose.yml` to point at your host project directory.
- Set `WATCH_PATH=/watched` (already set in `docker-compose.yml`).

#### Watching “any host path” (Docker)

When running in Docker, paths like `/home/kskroyal/...` exist on your host, not inside the container.  
If you want to paste **any absolute host path** into the UI and have it work, enable host path mapping:

- In `docker-compose.yml`, add:
  - volume: `"/:/host:ro"`
  - env: `HOST_FS_ROOT=/host`

Then you can paste a host path (e.g. `/home/kskroyal/Downloads/Priyanshu`) and the backend will resolve it to `/host/home/kskroyal/Downloads/Priyanshu` automatically.

---

## 🔧 Configuration

Before running the backend, create a `.env` file in the project root (or set environment variables) with your API keys and other settings.  
**Required variables:**

```env
OPENAI_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
DATABASE_URL=
HF_API_KEY=

# --- Social Media API Tokens ---
X_BEARER_TOKEN=
X_CONSUMER_KEY=
X_CONSUMER_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=

# --- LinkedIn API Tokens ---
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_ORGANIZATION_URN=
LINKEDIN_AUTHOR_URN=
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=

# --- App Secret ---
SECRET_KEY=
```

Tip: start from `.env.example`.

### API keys via UI (no code changes)

If an environment variable is set, the backend **uses it first**. If it is missing, the backend falls back to keys you saved from the UI.

1. Set `SECRET_KEY` (required to store keys securely)
2. Start the app
3. Open `http://localhost:8000/` → **⚙️ Settings**
4. Paste keys → **Save API Keys**
5. Use:
   - **Test Connections**: calls each provider with a lightweight request and shows only status codes (no secrets)
   - **Clear Saved Keys (DB)**: deletes all stored keys (env vars are unaffected)

---

## 🛠️ Usage

- Configure your `.env` file with the required API keys.
- Start the backend server.
- Use the FastAPI docs at [http://localhost:8000/](http://localhost:8000/) to interact with the API.
- The backend will monitor your specified folder for changes and generate/post content automatically.
- Approve, edit, or reject generated posts via the API endpoints.

---

## 🛣️ Roadmap Ahead

- Blog publishing support  
- More platform integrations  
- Post templates and customization  
- Analytics and notifications  

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.