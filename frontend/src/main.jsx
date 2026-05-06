import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { BookOpen, Check, Clock, FilePenLine, Library, Plus, Search, Send, Sparkles } from "lucide-react";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const emptyDraft = { title: "", author: "", summary: "", content: "", tags: "", status: "draft" };

function App() {
  const [articles, setArticles] = useState([]);
  const [activeSlug, setActiveSlug] = useState("");
  const [activeArticle, setActiveArticle] = useState(null);
  const [draft, setDraft] = useState(emptyDraft);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("published");
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadArticles(status, query);
  }, [query, status]);

  useEffect(() => {
    if (!activeSlug && articles.length > 0) {
      setActiveSlug(articles[0].slug);
    }
  }, [articles, activeSlug]);

  useEffect(() => {
    if (!activeSlug) return;
    fetch(`${API_URL}/articles/${activeSlug}`)
      .then((response) => {
        if (!response.ok) throw new Error("Article not found");
        return response.json();
      })
      .then(setActiveArticle)
      .catch(() => setActiveArticle(null));
  }, [activeSlug]);

  const stats = useMemo(() => {
    const published = articles.filter((article) => article.status === "published").length;
    const drafts = articles.filter((article) => article.status === "draft").length;
    return { published, drafts, total: articles.length };
  }, [articles]);

  function loadArticles(nextStatus = status, nextQuery = query) {
    setIsLoading(true);
    const params = new URLSearchParams({ status: nextStatus, q: nextQuery });
    fetch(`${API_URL}/articles?${params}`)
      .then((response) => response.json())
      .then((data) => {
        setArticles(data);
        setIsLoading(false);
      })
      .catch(() => {
        setArticles([]);
        setIsLoading(false);
        setMessage("API unavailable. Start the FastAPI server to publish and explore articles.");
      });
  }

  function updateDraft(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function submitArticle(event) {
    event.preventDefault();
    setMessage("");
    const payload = {
      ...draft,
      tags: draft.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
    };
    let response;
    try {
      response = await fetch(`${API_URL}/articles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch {
      setMessage("API unavailable. Start the FastAPI server and try again.");
      return;
    }
    if (!response.ok) {
      setMessage("Check the article fields and try again.");
      return;
    }
    const article = await response.json();
    setDraft(emptyDraft);
    setStatus("all");
    setActiveSlug(article.slug);
    setMessage(article.status === "published" ? "Article published." : "Draft saved.");
    loadArticles("all", query);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><BookOpen size={24} /></div>
          <div>
            <h1>ArticleHub</h1>
            <p>Write, publish, explore</p>
          </div>
        </div>
        <div className="search-box">
          <Search size={18} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search articles" />
        </div>
        <div className="status-tabs">
          {["published", "draft", "all"].map((option) => (
            <button className={status === option ? "active" : ""} key={option} onClick={() => setStatus(option)}>
              {option}
            </button>
          ))}
        </div>
        <section className="metrics" aria-label="Article metrics">
          <div><strong>{stats.total}</strong><span>Total</span></div>
          <div><strong>{stats.published}</strong><span>Live</span></div>
          <div><strong>{stats.drafts}</strong><span>Drafts</span></div>
        </section>
        <div className="article-list">
          {isLoading && <p className="muted">Loading articles...</p>}
          {!isLoading && articles.map((article) => (
            <button className={`article-row ${activeSlug === article.slug ? "selected" : ""}`} key={article.id} onClick={() => setActiveSlug(article.slug)}>
              <span>{article.title}</span>
              <small>{article.author}</small>
            </button>
          ))}
          {!isLoading && articles.length === 0 && <p className="muted">No articles found.</p>}
        </div>
      </aside>

      <section className="reader">
        {activeArticle ? (
          <article>
            <div className="article-kicker">
              <span className={activeArticle.status === "published" ? "pill live" : "pill"}>{activeArticle.status}</span>
              <span><Clock size={16} />{activeArticle.read_minutes} min read</span>
            </div>
            <h2>{activeArticle.title}</h2>
            <p className="summary">{activeArticle.summary}</p>
            <div className="byline">By {activeArticle.author}</div>
            <div className="tag-row">
              {activeArticle.tags.map((tag) => <span key={tag}>{tag}</span>)}
            </div>
            <p className="content">{activeArticle.content}</p>
          </article>
        ) : (
          <div className="empty-state">
            <Library size={44} />
            <h2>Select an article</h2>
            <p>Published stories and saved drafts will appear here.</p>
          </div>
        )}
      </section>

      <section className="composer">
        <div className="panel-heading">
          <div>
            <span className="eyebrow"><FilePenLine size={16} />Studio</span>
            <h2>Compose</h2>
          </div>
          <Sparkles size={22} />
        </div>
        <form onSubmit={submitArticle}>
          <label>Title<input value={draft.title} onChange={(event) => updateDraft("title", event.target.value)} required minLength={3} /></label>
          <label>Author<input value={draft.author} onChange={(event) => updateDraft("author", event.target.value)} required minLength={2} /></label>
          <label>Summary<textarea value={draft.summary} onChange={(event) => updateDraft("summary", event.target.value)} required minLength={10} rows={3} /></label>
          <label>Article body<textarea value={draft.content} onChange={(event) => updateDraft("content", event.target.value)} required minLength={40} rows={9} /></label>
          <label>Tags<input value={draft.tags} onChange={(event) => updateDraft("tags", event.target.value)} placeholder="React, FastAPI, Writing" /></label>
          <div className="publish-controls">
            <button type="button" className={draft.status === "draft" ? "active" : ""} onClick={() => updateDraft("status", "draft")}><Plus size={16} />Draft</button>
            <button type="button" className={draft.status === "published" ? "active" : ""} onClick={() => updateDraft("status", "published")}><Check size={16} />Publish</button>
          </div>
          <button className="primary-action" type="submit"><Send size={18} />Save article</button>
          {message && <p className="form-message">{message}</p>}
        </form>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
