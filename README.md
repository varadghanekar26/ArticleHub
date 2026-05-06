# ArticleHub

A full-stack article publishing platform built with FastAPI and React where users can write, publish, and explore articles.

## Features

- Compose articles with title, author, summary, body, tags, and draft/published status.
- Explore published articles, drafts, or the full library.
- Search articles by title, summary, author, or tags.
- Read full article details with estimated reading time.
- Persist content locally with SQLite.

## Run Locally

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The React app runs at `http://127.0.0.1:5173`.
