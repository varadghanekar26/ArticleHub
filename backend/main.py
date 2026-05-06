from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "articlehub.db"

app = FastAPI(title="ArticleHub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ArticleBase(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    author: str = Field(min_length=2, max_length=80)
    summary: str = Field(min_length=10, max_length=260)
    content: str = Field(min_length=40)
    tags: list[str] = Field(default_factory=list)
    status: Literal["draft", "published"] = "draft"


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=140)
    author: str | None = Field(default=None, min_length=2, max_length=80)
    summary: str | None = Field(default=None, min_length=10, max_length=260)
    content: str | None = Field(default=None, min_length=40)
    tags: list[str] | None = None
    status: Literal["draft", "published"] | None = None


class Article(ArticleBase):
    id: int
    slug: str
    read_minutes: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in slug.split("-") if part)[:80] or "article"


def estimate_read_minutes(content: str) -> int:
    return max(1, round(len(content.split()) / 220))


def serialize(row: sqlite3.Row) -> Article:
    return Article(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        author=row["author"],
        summary=row["summary"],
        content=row["content"],
        tags=[tag for tag in row["tags"].split(",") if tag],
        status=row["status"],
        read_minutes=row["read_minutes"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
    )


def unique_slug(conn: sqlite3.Connection, title: str, article_id: int | None = None) -> str:
    base = slugify(title)
    slug = base
    suffix = 2
    while True:
        params: tuple[str, ...] | tuple[str, int] = (slug,)
        clause = ""
        if article_id is not None:
            clause = " AND id != ?"
            params = (slug, article_id)
        exists = conn.execute(f"SELECT 1 FROM articles WHERE slug = ?{clause}", params).fetchone()
        if not exists:
            return slug
        slug = f"{base}-{suffix}"
        suffix += 1


@app.on_event("startup")
def startup() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                summary TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL,
                status TEXT NOT NULL,
                read_minutes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) AS count FROM articles").fetchone()["count"]
        if count == 0:
            seed_articles(conn)


def seed_articles(conn: sqlite3.Connection) -> None:
    samples = [
        ArticleCreate(
            title="Building Better Editorial Workflows",
            author="Maya Chen",
            summary="How lightweight structure helps small teams move ideas from draft to published without losing momentum.",
            content=(
                "A healthy publishing workflow gives writers enough shape to move quickly without turning every article "
                "into a project management ceremony. Start with a clear brief, capture the intended reader, and keep "
                "feedback close to the draft. The best systems make ownership obvious, keep revision history calm, and "
                "let editors focus on meaning instead of chasing files."
            ),
            tags=["Editorial", "Workflow", "Teams"],
            status="published",
        ),
        ArticleCreate(
            title="What Makes Technical Articles Useful",
            author="Jon Bell",
            summary="Useful technical writing starts with context, keeps examples honest, and respects the reader's time.",
            content=(
                "Technical readers arrive with a job to do. They need context, a working path, and enough caveats to make "
                "good decisions in their own codebase. A strong article names the problem early, shows the smallest useful "
                "example, and then explains the tradeoffs that appear when the work becomes real."
            ),
            tags=["Writing", "Engineering"],
            status="published",
        ),
    ]
    for article in samples:
        create_article(conn, article)


def create_article(conn: sqlite3.Connection, article: ArticleCreate) -> Article:
    now = utc_now()
    published_at = now if article.status == "published" else None
    cursor = conn.execute(
        """
        INSERT INTO articles
            (slug, title, author, summary, content, tags, status, read_minutes, created_at, updated_at, published_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            unique_slug(conn, article.title),
            article.title,
            article.author,
            article.summary,
            article.content,
            ",".join(article.tags),
            article.status,
            estimate_read_minutes(article.content),
            now,
            now,
            published_at,
        ),
    )
    row = conn.execute("SELECT * FROM articles WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return serialize(row)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/articles", response_model=list[Article])
def list_articles(
    status: Literal["all", "draft", "published"] = "published",
    q: str = Query(default="", max_length=120),
) -> list[Article]:
    clauses: list[str] = []
    params: list[str] = []
    if status != "all":
        clauses.append("status = ?")
        params.append(status)
    if q:
        clauses.append("(title LIKE ? OR summary LIKE ? OR author LIKE ? OR tags LIKE ?)")
        needle = f"%{q}%"
        params.extend([needle, needle, needle, needle])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM articles {where} ORDER BY COALESCE(published_at, updated_at) DESC",
            params,
        ).fetchall()
        return [serialize(row) for row in rows]


@app.get("/articles/{slug}", response_model=Article)
def get_article(slug: str) -> Article:
    with connect() as conn:
        row = conn.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return serialize(row)


@app.post("/articles", response_model=Article, status_code=201)
def post_article(article: ArticleCreate) -> Article:
    with connect() as conn:
        return create_article(conn, article)


@app.patch("/articles/{article_id}", response_model=Article)
def update_article(article_id: int, updates: ArticleUpdate) -> Article:
    if hasattr(updates, "model_dump"):
        changes = updates.model_dump(exclude_unset=True)
    else:
        changes = updates.dict(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No changes supplied")

    with connect() as conn:
        current = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        if current is None:
            raise HTTPException(status_code=404, detail="Article not found")

        data = dict(current)
        data.update(changes)
        now = utc_now()
        if changes.get("title"):
            data["slug"] = unique_slug(conn, data["title"], article_id)
        if changes.get("content"):
            data["read_minutes"] = estimate_read_minutes(data["content"])
        if changes.get("status") == "published" and not data["published_at"]:
            data["published_at"] = now
        if changes.get("status") == "draft":
            data["published_at"] = None

        conn.execute(
            """
            UPDATE articles
            SET slug = ?, title = ?, author = ?, summary = ?, content = ?, tags = ?, status = ?,
                read_minutes = ?, updated_at = ?, published_at = ?
            WHERE id = ?
            """,
            (
                data["slug"],
                data["title"],
                data["author"],
                data["summary"],
                data["content"],
                ",".join(data["tags"]) if isinstance(data["tags"], list) else data["tags"],
                data["status"],
                data["read_minutes"],
                now,
                data["published_at"],
                article_id,
            ),
        )
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return serialize(row)


@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int) -> None:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Article not found")

@app.get("/")
def home():
    return {"message": "ArticleHub API Running"}