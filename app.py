"""Sober — an AI companion that never forgets the night before.

Built on the Cognee memory engine. Every message is stored in a persistent
graph-vector memory (remember), and every reply is grounded in everything Cognee
has ever learned about you (recall) — so context survives across sessions and
never overflows the model's context window.

Runs two ways from the SAME code:
  • Local open-source Cognee  (Track 1)  — default
  • Cognee Cloud              (Track 2)  — set COGNEE_CLOUD_URL + COGNEE_CLOUD_API_KEY
"""

import os
import pathlib
import json
import glob
import re
import asyncio

# Single-user mode (no auth, shared local DBs) — must be set before importing cognee.
os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "false")

from dotenv import load_dotenv

load_dotenv()

import litellm
import cognee
from cognee import SearchType
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = pathlib.Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
GRAPH_HTML = STATIC_DIR / "graph.html"
DATASET = "sober_memory"

# ── Cloud vs local toggle ──────────────────────────────────────────────────
CLOUD_URL = os.getenv("COGNEE_CLOUD_URL")
CLOUD_KEY = os.getenv("COGNEE_CLOUD_API_KEY")
USE_CLOUD = bool(CLOUD_URL and CLOUD_KEY)

_cloud = None
if USE_CLOUD:
    from cognee.api.v1.serve.cloud_client import CloudClient

    _cloud = CloudClient(CLOUD_URL, CLOUD_KEY)
else:
    # Keep all Cognee data inside the project so memory persists across restarts.
    cognee.config.data_root_directory(str(BASE_DIR / ".cognee_data"))
    cognee.config.system_root_directory(str(BASE_DIR / ".cognee_system"))


async def mem_remember(text: str, run_in_background: bool = False):
    if USE_CLOUD:
        return await _cloud.remember(text, dataset_name=DATASET, run_in_background=run_in_background)
    return await cognee.remember([text], dataset_name=DATASET, run_in_background=run_in_background)


async def mem_recall(query: str):
    if USE_CLOUD:
        return await _cloud.recall(
            query_text=query, query_type="GRAPH_COMPLETION", datasets=[DATASET]
        )
    return await cognee.recall(
        query_text=query, query_type=SearchType.GRAPH_COMPLETION, datasets=[DATASET]
    )


async def update_shared_context():
    """Retrieve all nodes from the knowledge graph and write a unified markdown context file."""
    if USE_CLOUD:
        return
    
    from cognee.infrastructure.databases.graph import get_graph_engine
    try:
        ge = await get_graph_engine()
        nodes, edges = await ge.get_graph_data()
    except Exception:
        return

    facts = []
    seen = set()
    # Generic entity labels that add noise rather than signal to the context file.
    blacklisted_exact = {
        "system", "document", "file", "information", "date", "search",
        "topic", "question", "sober", "bot", "user", "the speaker",
        "speaker", "name",
    }

    for n in nodes:
        if isinstance(n, (list, tuple)) and len(n) >= 2:
            props = n[1]
        elif isinstance(n, dict):
            props = n
        else:
            props = {}
        
        if not isinstance(props, dict):
            continue
            
        for k in ("text", "summary", "content", "description", "name"):
            v = props.get(k)
            if v and isinstance(v, str) and len(v.strip()) > 3:
                val = v.strip()
                val_lower = val.lower()
                
                # Filter out raw system IDs, metadata names and generic labels
                if re.match(r"^text_[0-9a-f]{32}$", val_lower):
                    continue
                if val_lower in blacklisted_exact:
                    continue
                if val_lower.startswith("the file containing"):
                    continue
                if len(val.split()) < 2:
                    continue
                if val_lower in ("sober replied.", "sober replied:", "sober replied", "user said:", "user said."):
                    continue
                
                if val not in seen:
                    seen.add(val)
                    facts.append(val)
                break

    context_file = BASE_DIR / "claude.md"
    content = [
        "# Sober Unified Memory Context",
        "<!-- This file is automatically synchronized by Sober. Do not edit manually. -->",
        "",
        "The following is a list of facts and context synced across your AI sessions:",
        ""
    ]
    if facts:
        for f in sorted(facts):
            content.append(f"- {f}")
    else:
        content.append("- No memories stored yet.")
    content.append("")
    
    with open(context_file, "w", encoding="utf-8") as f:
        f.write("\n".join(content))


async def schedule_context_update():
    async def task():
        await asyncio.sleep(4)  # Wait for pipeline to finish processing
        await update_shared_context()
    asyncio.create_task(task())


_SYSTEM_PROMPT = (
    "You are Sober, an AI assistant with a persistent memory graph that spans multiple "
    "AI tools and sessions. Answer the user's question using ONLY the memory context "
    "provided. If the context doesn't contain enough information, be honest and specific "
    "about what you do and don't have in memory — never make things up. "
    "Keep replies short and conversational."
)


async def _llm_reply(context: str, question: str) -> str:
    resp = await litellm.acompletion(
        model=os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
        api_key=os.getenv("LLM_API_KEY"),
        api_base=os.getenv("LLM_ENDPOINT") or None,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Memory context:\n{context}\n\nQuestion: {question}"},
        ],
        max_tokens=256,
    )
    return resp.choices[0].message.content.strip()


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Sober")


class ChatIn(BaseModel):
    message: str


@app.post("/chat")
async def chat(body: ChatIn):
    """Remember the user's message, then recall an answer grounded in all memory."""
    await mem_remember(f"User said: {body.message}", run_in_background=True)

    results = await mem_recall(body.message)

    if USE_CLOUD:
        # Cloud: Cognee handles the LLM completion step itself.
        top = results[0] if results else None
        reply = (
            getattr(top, "text", None)
            or (top.get("text") if isinstance(top, dict) else None)
            or str(top)
            if top else "I don't have anything in memory about that yet."
        )
    else:
        # Local: gather raw context from all recall results, then generate a
        # proper conversational reply via the configured LLM.
        parts = []
        for r in (results or [])[:5]:
            t = getattr(r, "text", None) or (r.get("text") if isinstance(r, dict) else None) or str(r)
            if t and len(t.strip()) > 4:
                parts.append(t.strip())
        context = "\n\n".join(parts) if parts else "No relevant memory found."
        try:
            reply = await _llm_reply(context, body.message)
        except Exception:
            reply = parts[0] if parts else "I don't have anything in memory about that yet."

        reply = str(reply or "").strip()
        if not reply:
            reply = parts[0] if parts else "I don't have anything in memory about that yet."

    await mem_remember(f"Sober replied: {reply}", run_in_background=True)
    await schedule_context_update()
    return {"reply": reply, "backend": "cloud" if USE_CLOUD else "local"}


@app.post("/graph")
async def build_graph():
    """Render the current knowledge graph to an interactive HTML file (local mode)."""
    if USE_CLOUD:
        return {
            "ok": False,
            "error": "On Cognee Cloud the graph lives in your cloud dashboard at my.cognee.ai.",
        }
    STATIC_DIR.mkdir(exist_ok=True)
    await cognee.visualize_graph(destination_file_path=str(GRAPH_HTML), dataset=DATASET)
    return {"ok": True, "url": "/static/graph.html"}


@app.post("/forget")
async def forget():
    """Wipe all memory (sober up completely)."""
    if USE_CLOUD:
        await _cloud.forget()
    else:
        await cognee.forget(everything=True)
        if GRAPH_HTML.exists():
            GRAPH_HTML.unlink()
    
    context_file = BASE_DIR / "claude.md"
    if context_file.exists():
        context_file.unlink()
    return {"ok": True}


@app.get("/api/status")
async def get_status():
    """Return status of memory context file synchronization."""
    claude_md_exists = (BASE_DIR / "claude.md").exists()
    home = pathlib.Path.home()
    claude_code_logs = glob.glob(str(home / ".claude" / "projects" / "**" / "*.jsonl"), recursive=True)
    return {
        "claude_md": claude_md_exists,
        "claude_code": len(claude_code_logs) > 0,
    }


@app.get("/api/graph")
async def api_graph():
    """Return the knowledge graph as JSON nodes/edges for the custom visualizer."""
    if USE_CLOUD:
        return {"nodes": [], "edges": []}
    from cognee.infrastructure.databases.graph import get_graph_engine

    try:
        ge = await get_graph_engine()
        nodes, edges = await ge.get_graph_data()
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}

    def label(props):
        if isinstance(props, dict):
            for k in ("name", "text", "summary", "content", "description", "type"):
                v = props.get(k)
                if v:
                    return str(v)[:48]
        return str(props)[:32]

    out_nodes, seen = [], set()
    for i, n in enumerate(nodes):
        if isinstance(n, (list, tuple)) and len(n) >= 2:
            nid, props = n[0], n[1]
        elif isinstance(n, dict):
            nid, props = n.get("id", i), n
        else:
            nid, props = n, {}
        nid = str(nid)
        if nid in seen:
            continue
        seen.add(nid)
        t = props.get("type") if isinstance(props, dict) else None
        out_nodes.append({"id": nid, "label": label(props), "type": str(t or "Node")})

    out_edges = []
    for e in edges:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            src, tgt = str(e[0]), str(e[1])
            rel = str(e[2]) if len(e) > 2 else ""
        elif isinstance(e, dict):
            src = str(e.get("source_node_id") or e.get("source") or "")
            tgt = str(e.get("target_node_id") or e.get("target") or "")
            rel = str(e.get("relationship_name") or e.get("label") or "")
        else:
            continue
        if src in seen and tgt in seen:
            out_edges.append({"source": src, "target": tgt, "label": rel})
    return {"nodes": out_nodes, "edges": out_edges}


_SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_\-]{12,}|gsk_[A-Za-z0-9_\-]{12,}|AIza[A-Za-z0-9_\-]{20,}|\b[a-f0-9]{40,}\b)"
)


def _redact(t: str) -> str:
    return _SECRET_RE.sub("[redacted]", t)


def _extract_text(raw: str) -> str:
    """Pull conversation text out of a pasted export (JSON or plain text)."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except Exception:
        return raw  # plain text
    out = []

    def walk(o):
        if isinstance(o, str):
            if len(o) > 1:
                out.append(o)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, dict):
            for k in ("parts", "content", "text", "value", "message", "body", "mapping",
                      "messages", "conversations"):
                if k in o:
                    walk(o[k])

    walk(data)
    return "\n".join(out) if out else raw


def _content_to_text(c) -> str:
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text" and b.get("text"):
                parts.append(b["text"])
            elif isinstance(b, str):
                parts.append(b)
        return " ".join(parts)
    return ""


def _clean_long_words(text: str) -> str:
    """Filter out any single word/token longer than 1000 characters to prevent Cognee chunker crash."""
    words = text.split()
    cleaned = []
    for w in words:
        if len(w) > 1000:
            continue
        cleaned.append(w)
    return " ".join(cleaned)


@app.post("/import")
async def import_history(req: Request):
    """Ingest a pasted/uploaded AI-tool export into unified memory."""
    body = await req.json()
    source = str(body.get("source") or "AI tool")
    text = _redact(_extract_text(body.get("text") or ""))[:20000]
    text = _clean_long_words(text)
    if not text.strip():
        return {"ok": False, "error": "No readable text found in that import."}
    await mem_remember(f"[Imported from {source}] {text}", run_in_background=True)
    await schedule_context_update()
    return {"ok": True, "source": source, "chars": len(text)}


@app.post("/import/local")
async def import_local():
    """Ingest the user's local Claude Code transcripts into unified memory."""
    home = pathlib.Path.home()
    files = sorted(
        glob.glob(str(home / ".claude" / "projects" / "**" / "*.jsonl"), recursive=True),
        key=lambda f: os.path.getmtime(f),
        reverse=True,
    )[:3]
    if not files:
        return {"ok": False, "error": "No Claude Code transcripts found in ~/.claude/projects."}
    msgs = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    m = obj.get("message") if isinstance(obj, dict) else None
                    txt = _content_to_text(m.get("content")) if isinstance(m, dict) else ""
                    if txt and len(txt) > 2:
                        msgs.append(txt)
        except Exception:
            continue
    text = _redact("\n".join(msgs))
    text = re.sub(r"[^\x09\x0a\x20-\x7e]", " ", text)  # printable-ascii only
    text = re.sub(r"\s+", " ", text).strip()[:6000]
    text = _clean_long_words(text)
    if not text:
        return {"ok": False, "error": "No readable transcript text."}
    try:
        await mem_remember(f"[Imported from Claude Code] {text}", run_in_background=True)
        await schedule_context_update()
    except Exception as e:
        return {"ok": False, "error": f"Ingest failed: {e}"}
    return {"ok": True, "source": "Claude Code", "files": len(files), "chars": len(text)}


_GENERIC_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com",
    "icloud.com", "proton.me", "protonmail.com", "live.com", "aol.com",
}


@app.post("/profile")
async def profile(req: Request):
    """Seed the signed-in user's identity into memory so Sober knows who they are."""
    body = await req.json()
    email = str(body.get("email") or "").strip()
    if "@" not in email:
        return {"ok": False, "error": "no email"}
    local, domain = email.split("@", 1)
    name = " ".join(p.capitalize() for p in re.split(r"[._\-+]+", local) if p) or local
    facts = [f"My name is {name}.", f"My email is {email}."]
    if domain.lower() not in _GENERIC_DOMAINS:
        facts.append(
            f"I work at the company whose domain is {domain}; my work email is {email}."
        )
    await mem_remember(" ".join(facts), run_in_background=True)
    await schedule_context_update()
    return {"ok": True, "name": name, "domain": domain}


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.exception_handler(Exception)
async def on_error(request, exc):
    return JSONResponse(status_code=500, content={"error": str(exc)})


STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
