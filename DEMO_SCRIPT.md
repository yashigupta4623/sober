# 🎬 Sober — 2-minute demo video script

**Goal:** show the problem → the product → the "wow" (cross-tool memory + live graph) → the close.
**Setup before recording:** server running (`uvicorn app:app`), memory reset (click **Reset** on the demo graph), sign-in fresh, browser at `http://localhost:8000`. Use a sturdy LLM (OpenAI gpt-4o-mini) so you don't hit rate limits mid-record.

---

### 0:00–0:12 — Hook: Curing the AI Hangover (screen: hero)
> "Every AI tool you use has amnesia. You close the tab or switch tools, and they wake up with a context hangover — asking, where is my memory? Sober is the persistent memory layer that cures the AI hangover."

*Action:* land on the hero, let the headline + product-mockup animation play. Scroll slowly past the trust strip.

### 0:12–0:30 — The problem, made concrete (screen: Problem section)
> "Stateless models lose the thread. Ask a normal chatbot what breed your dog is, and it shrugs."

*Action:* show the "One forgets. One remembers." side-by-side. Pause on the stateless card fading to *"I don't have that information 🤷"*.

### 0:30–0:50 — Sign in → connect your history (screen: Get started → onboarding)
> "Sober is one memory layer across all of them. Sign in once…"

*Action:* click **Get started**, enter your work email. Onboarding "Connect your AI history" appears.
> "…and connect the tools you already use. Claude Code is instant — it reads your local history."

*Action:* click **Claude Code → Connect**. Show "Connected ✓".

### 0:50–1:20 — Cognee ECL Pipeline & Auto-Sync (screen: live demo + workspace)
> "Sober sends every message, CLI transcript, and web export through Cognee's ECL pipeline — Extract, Cognify, and Load. It automatically extracts structured entities and maps them into Cognee's local graph database. Let's see it live."

*Action:* scroll to the demo. Type: *"I'm building a portfolio site, and my dog's name is Pixel."* → send. Watch the graph **grow a new node** in real time.
> "But Sober doesn't keep this graph locked up. It queries Cognee's graph engine, compiles your memory nodes, and updates a unified context file (`claude.md`) right in your workspace."

*Action:* Open your code editor side-by-side, show **[claude.md](file:///Users/yashigupta/Downloads/sober/claude.md)** file updating in real-time with the new facts: *"Pixel is a beagle."*, *"Building portfolio site."*

### 1:20–1:45 — Cross-Tool Sync in action (screen: terminal/editor)
> "This means context follows you instantly. If one AI tool runs out of limits, you can open Claude Code or Cursor, and they will read `claude.md` to pick up right where you left off — with zero manual exports."

*Action:* Open terminal, start Claude Code or Cursor, and ask: *"Who is my dog and what project am I working on?"* Show the AI answering correctly using the local `claude.md` context.

### 1:45–1:55 — Why Cognee wins (screen: Comparison / How it works)
> "Unlike naive chatbots that stuff your whole history into the prompt causing window overflow and high API bills, Cognee uses hybrid vector-graph retrieval to fetch only the precise slice of memory. Flat token costs, sharp recall."

*Action:* show the "Flat cost. Sharp recall." comparison bars.

### 1:55–2:05 — Close (screen: CTA)
> "Sober. Curing AI amnesia and context hangovers, one memory graph at a time. Open source, self-hosted, built on Cognee."

*Action:* end on the dark CTA band + logo.

---

### Recording tips
- 1080p, system audio off, clean browser (hide bookmarks bar).
- Keep cursor movements slow and deliberate.
- Pre-load some memory so the graph already looks rich, then add one node live for the "it updates" moment.
- Keep it under 2:10. Energy high, no dead air.
