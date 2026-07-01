# Sober: I gave my AI tools one shared memory — here's how, with Cognee

*Built for the WeMakeDevs × Cognee "Hangover Part AI" hackathon.*

## The problem nobody admits

I use four AI tools in a day. I'll start a feature in ChatGPT, move the prompt to Claude when I want a second opinion, and finish the actual code in Claude Code. By the third tool I've re-explained my project three times — because every LLM call is **stateless**. It doesn't remember the last session, and long context just overflows the window.

My agent woke up in Vegas with no memory of last night. That's the whole joke of the hackathon theme — and it's a real, daily, expensive problem.

## What I built: Sober

**Sober is one memory layer across every AI tool you use.** Sign in, connect your history (ChatGPT, Claude, Gemini, Claude Code), and Sober unifies it into a single **knowledge graph** you can recall from anywhere. It's built entirely on open-source [Cognee](https://github.com/topoteretes/cognee).

The point isn't "store my chats" — a notepad does that. The point is that Cognee turns scattered conversation into a **graph of entities and relationships**, so recall actually behaves like memory: it connects facts instead of just searching text.

## How it works — the Cognee memory lifecycle

Sober is a thin product layer over four Cognee calls:

| Action | Cognee API |
|---|---|
| Store a message / import history | `remember()` |
| Answer from memory | `recall(query, GRAPH_COMPLETION)` |
| Visualize the graph | `visualize_graph()` |
| Wipe everything | `forget(everything=True)` |

Every message runs `remember()`, which ingests the text, extracts entities/relationships with an LLM, embeds them, and commits edges to the graph. Answering runs `recall()`, which traverses that graph and completes — grounded, not guessed. Because it retrieves only the relevant subgraph, **token cost stays flat** as the conversation grows, instead of exploding the way naive history-stuffing does.

## The part I'm proud of: a unified, cross-tool memory

The differentiator is the **"Connect your AI history"** flow. The honest engineering reality is that you *can't* live-pull your ChatGPT/Gemini/Claude web history — there's no public API for it. So Sober uses the two paths that genuinely work:

- **Local CLI tools** (Claude Code, Codex, Cursor) store transcripts on disk — Sober reads those directly. One click, no upload.
- **Web tools** (ChatGPT, Claude, Gemini) — Sober opens the tool's export page, you drop the file, and it's ingested.

All of it lands in one graph. Sign in with a work email and Sober even seeds your profile (name, company-from-domain) so it knows who you are from the first message. Ask *"which company do I work for?"* and it answers — because the context is finally in one place.

## The build

- **Backend:** Python + FastAPI. Endpoints for chat, import (paste/upload + local transcripts), profile seeding, and a custom `/api/graph` that serializes Cognee's graph to JSON.
- **Frontend:** a single page — a dark product-style hero with a live memory mockup, then a custom **force-directed graph rendered from scratch on canvas** (not the default visualizer), colored by node type, that grows as you chat.
- **Models:** Groq (free) for chat + Gemini embeddings — fully free to run. Swappable, because Cognee is provider-agnostic.
- **Privacy:** local-first. The graph lives on your machine; secrets in transcripts are redacted before ingest.

## What I learned

1. **Cognee's graph beats flat RAG for "memory."** Connecting entities makes recall feel intentional.
2. **Be honest about what's possible.** No fake "auto-pull your ChatGPT history" button — export + local transcripts are the real, shippable paths.
3. **A memory layer is a *product*, not a feature.** The value is unifying context across tools, not storing it in one more silo.

## Try it

Open source, self-hosted, built on Cognee. [github.com/topoteretes/cognee](https://github.com/topoteretes/cognee)

*Your agent doesn't have to wake up in Vegas.*
