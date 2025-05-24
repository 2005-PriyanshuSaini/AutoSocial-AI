# AutoSocial AI

AutoSocial AI is a Python automation project that helps you create social media posts or blog content based on your local development work. It watches a folder (like your codebase), detects updates, and generates content that can be posted to platforms like Twitter (X), LinkedIn, or your personal website.

![AutoSocial AI Demo](https://via.placeholder.com/700x300?text=AutoSocial+AI+Demo+Coming+Soon)

---

## 👤 Author

**Priyanshu Saini**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin)](https://www.linkedin.com/in/priyanshu-saini-4b4a0a28a/)
[![Twitter](https://img.shields.io/badge/X-1DA1F2?style=flat&logo=twitter)](https://twitter.com/Dev_Priyanshu_1)
[![Linktree](https://img.shields.io/badge/Linktree-43e55b?style=flat&logo=linktree)](https://linktr.ee/Priyanshu_Saini2005)

📧 **Email:** [Priyanshusaini9991@gmail.com](mailto:Priyanshusaini9991@gmail.com)  
📄 [Resume (PDF)](https://drive.google.com/file/d/1-2z_mVgygun_uHoySuZBhAwvxqfFnBQC/view?usp=sharing)

---

## 🚧 Project Status

This project is currently in development.

- ✅ Backend: FastAPI (working)  
- 🚧 Frontend: In progress

---

## ✨ Features

- Monitors a folder for file changes  
- Generates text content using AI  
- Can create short posts (e.g. Twitter, LinkedIn) or long posts (e.g. blogs)  
- Can post to multiple platforms  
- Option to post instantly or on a schedule

---

## ⚙️ How It Works

1. You give AutoSocial AI access to your project folder.  
2. It checks for updates or changes in the codebase.  
3. Based on the changes, it generates a post like:

   > Added login system using FastAPI + JWT. Working well! 🔐  
   > #FastAPI #Python #DevLog

4. It then posts this content to Twitter, LinkedIn, or your portfolio.

![Workflow Example](https://via.placeholder.com/600x250?text=Example+Workflow+Image)


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
  > http://localhost:8000/docs

---

## 🔧 Configuration

Before running the backend, create a `.env` file in the project root (or set environment variables) with your API keys and other settings:

```env
OPENAI_API_KEY=
CLAUDE_API_KEY=
DEEPSEEK_API_KEY=
GEMINI_API_KEY=

DATABASE_URL=
```

---

## ⚙️ How It Works

1. You give AutoSocial AI access to your project folder.  
2. It monitors file changes and detects updates.  
3. Based on those changes, it generates social media or blog posts automatically.  
4. It posts the content to configured platforms or your portfolio.

---

## ✨ Features

- Folder monitoring for code changes  
- AI-generated post and blog content  
- Multi-platform posting support  
- Scheduling and instant post options  

---

## 🚧 Project Status

- Backend (FastAPI): ✅  
- Frontend: In progress  

---

## 🛣️ Roadmap

- Frontend dashboard for post management  
- Blog publishing support  
- More platform integrations  
- Post templates and customization  
- Analytics and notifications  

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.