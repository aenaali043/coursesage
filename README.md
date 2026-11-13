# CourseSage — an AI study agent built on one Python + AI course

**Built by Aena Ali** · Python 3.10+ · zero dependencies

CourseSage is a working agent, not a prompt: it retrieves from the video transcript,
runs code to check what Python actually does, cites the timestamp it used, and can write
quizzes and study plans to disk. It is grounded in **"Best Python + AI Full Course"**
(`youtube.com/watch?v=J9BI0jGOds8`, 13 h 02 m):

| track | time range | content |
|---|---|---|
| Python | 00:00:00 – 10:48:00 | install → data types → strings, slicing → operators → if/elif → loops → lists, tuples, sets, dicts → comprehensions → functions → `*args`/`**kwargs` → scope → first-class functions → lambda |
| AI | 10:49:01 – 13:01:56 | what AI is → tokens & prompting → hallucination → context engineering → tools → tokens as currency → vectors → context window → parameters → attention → transformers → fine-tuning → RLHF → RAG → MCP → agentic AI |

---

## Quick start (3 steps)

```bash
cd coursesage
cp .env.example .env          # then paste your API key into .env
python run.py doctor          # sanity check: config + knowledge base
python run.py                 # start chatting in the terminal
```

Want a browser instead of the terminal?

```bash
python run.py serve           # http://127.0.0.1:8000
```

Nothing to install: the project uses only the Python standard library.

### Windows one-click

Double-click `start.bat` — it starts the server and opens `http://127.0.0.1:8000`.
Keep that window open while you use the app.

### Running it on another machine

Anyone who clones this repo needs only:

1. **Python 3.10+** — check with `python --version`
2. **Their own API key** — copy `.env.example` to `.env` and paste a key.
   `.env` is gitignored, so no key ever reaches GitHub.
3. `python run.py doctor` then `python run.py serve` (or `start.bat` on Windows)

`127.0.0.1:8000` works only on the machine running the server — there is no public demo URL.

---

## Choosing a model

Set `LLM_PROVIDER` in `.env`. Any OpenAI-compatible endpoint works.

| provider | `.env` | notes |
|---|---|---|
| OpenAI | `LLM_PROVIDER=openai` + `OPENAI_API_KEY` | default, `gpt-4o-mini` |
| Google Gemini | `LLM_PROVIDER=gemini` + `GEMINI_API_KEY` | free tier, `gemini-3.1-flash-lite` |
| Ollama (local, free) | `LLM_PROVIDER=ollama` | needs `ollama pull qwen2.5:7b` |
| Groq / OpenRouter / any | `LLM_PROVIDER=groq` / `openrouter`, or set `LLM_BASE_URL` + `LLM_API_KEY` | pick any hosted model |

If a provider rejects native tool calling, the agent automatically falls back to a
text protocol (`TOOL:` / `ARGS:`) — that is what `TOOL_MODE=auto` does. Force either
path with `TOOL_MODE=native` or `TOOL_MODE=text`.

---

## What the agent can do

```
python run.py                        interactive chat
python run.py serve [port]           web UI
python run.py outline [Python|AI]    chapter map with timestamps
python run.py search "slicing step"  raw retrieval, no model call, no key needed
python run.py doctor                 config + knowledge-base check
```

Inside the chat:

| command | effect |
|---|---|
| `/outline [Python\|AI]` | chapter list |
| `/search <query>` | transcript search |
| `/quiz <topic> [n]` | generated quiz with answers |
| `/plan <topic> [days]` | day-by-day study plan |
| `/notes` | saved notes |
| `/steps <n>` | tool-call budget per turn |
| `/verbose` | show tool tracing |
| `/reset` | clear the conversation |

### Tools

| tool | what it does |
|---|---|
| `search_course` | BM25 search over 428 transcript passages, returns timestamps + links |
| `course_outline` | 53-chapter map so the agent can point you somewhere |
| `transcript_window` | pulls everything said around a timestamp |
| `run_python` | runs a snippet in a subprocess (10 s timeout) and shows real output |
| `save_note` / `recall_notes` | persistent study notes in `data/notes.md` |

The agent decides which to call, may chain several calls in one turn, and is told never to
invent a timestamp — links can only come from tool output.

---

## How it works

```
question
   │
   ▼
CourseAgent.ask ──► LLM (tools attached)
   │                    │
   │        tool_calls? ├── yes ──► ToolBox ──► KB / subprocess ──┐
   │                    │                                          │
   │                    └── no ──► final answer (cites [mm:ss])    │
   └────────────────────────── observe result ◄────────────────────┘
```

```
coursesage/
├── run.py                  entry point (chat / serve / outline / search / doctor)
├── build_kb.py             rebuild the knowledge base from the raw transcript
├── data/
│   ├── transcript_raw.json 1 628 caption segments
│   ├── course_chunks.json  428 timestamped passages (generated)
│   ├── chapters.json       53 curated chapters with descriptions
│   └── notes.md            created when the agent saves a note
├── coursesage/
│   ├── agent.py            the tool-calling loop, duplicate-call guard, step budget
│   ├── kb.py               BM25 + chapter boosts + synonym expansion for ASR spellings
│   ├── tools.py            tool schemas and implementations
│   ├── llm.py              urllib client for any /chat/completions endpoint
│   ├── prompts.py          tutor persona and grounding rules
│   ├── cli.py, server.py   terminal UI, stdlib HTTP UI
│   └── static/index.html   single-page chat interface
├── examples/mock_llm.py    fake model server for offline testing
└── tests/test_smoke.py     14 tests, no API key required
```

**Retrieval details.** Chunks are ~2 000 characters, cut at chapter boundaries so each
passage carries the right chapter label. Scoring is BM25 plus two corrections that matter a
lot here: a boost for passages from a chapter whose title/description matches the question,
and a coverage factor so one rare word cannot win alone. A synonym table bridges
auto-caption spellings — `*args` is transcribed as "arcs/ars", `**kwargs` as "kwords/kwax" —
so typing `kwargs` still finds the right section.

**Grounding.** The system prompt forbids inventing timestamps, requires a `search_course`
call before explaining course material, and asks the agent to label anything outside the
course as "(not in the course)".

---

## Tests

```bash
python -m unittest discover -s tests -v
```

Covers retrieval quality (query → expected chapter), the timestamp parser, every tool,
note persistence, and both agent modes against `examples/mock_llm.py`. No API key needed.

---

## Cost and limits

- Each turn is 1–3 model calls; retrieval is local, so context stays small (~4–8 k tokens on
  a search-heavy turn).
- `run_python` executes code on **your machine** with a 10 s timeout and no network guard.
  It is a teaching tool: do not paste untrusted code. Set `ALLOW_CODE_EXEC=0` in the
  environment if you want it disabled.
- Transcript passages are auto-captioned and contain speech-recognition noise; the prompt
  tells the model to read through it silently rather than quote it.
- Answers are grounded in this one course. For anything else, the agent says so and switches
  to general knowledge.

---

## Ideas to extend it

- Swap BM25 for embeddings: implement `search()` in `kb.py` against an `/embeddings`
  endpoint and keep the same `Hit` shape — nothing else changes.
- Add a `progress.json` tool that tracks which chapters you finished, and let `/plan` read it.
- Add a tool that runs a learner's solution against test cases (pytest subprocess) for
  auto-grading exercises.
- Point `build_kb.py` at a different transcript and the whole agent retargets to that course.
