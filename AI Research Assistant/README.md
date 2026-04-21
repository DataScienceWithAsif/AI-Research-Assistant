# AI Research Assistant

A multi-agent research paper generator built with **LangGraph**, **Groq**, and **Tavily**.
Enter any topic — the pipeline searches the web, plans, writes, evaluates, and refines a complete research paper automatically.

---

## Project Structure

```
research_assistant/
│
├── graph.py          ← LangGraph pipeline (all agent logic lives here)
├── app.py            ← Streamlit interface (UI only, imports from graph.py)
├── requirements.txt  ← Python dependencies
├── .env              ← Your API keys (create this yourself)
└── README.md
```

---

## Pipeline Flow

```
START
  ↓
query_generator   — LLM generates 3–6 targeted search queries
  ↓
webSearch         — All queries run in parallel (RunnableParallel)
  ↓
planner           — LLM plans paper sections from search results
  ↓
writer            — LLM writes the full paper
  ↓
evaluator         — LLM reviews quality (yes/no + feedback)
  ↓ (if needs improvement and revisions < max)
rewriter          — LLM rewrites based on feedback ──→ back to evaluator
  ↓ (approved or max revisions reached)
save_paper        — Returns final paper
  ↓
END
```

---

## Setup

### 1. Clone / download the project

```bash
cd research_assistant
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your `.env` file

```
GROQ_API_KEY=your_groq_key_here
TAVILY_API_KEY=your_tavily_key_here
```

Get your keys:
- Groq: https://console.groq.com
- Tavily: https://tavily.com

### 4. Run the app

```bash
streamlit run app.py
```

---

## Features

- **Parallel web search** — all queries fire at the same time
- **Self-evaluation loop** — paper is reviewed and rewritten if needed
- **Live streaming UI** — see each pipeline step as it runs
- **Word-by-word paper reveal** — writing feels alive
- **HTML download** — export a beautiful formatted paper to your machine
- **Revision cap** — configurable (1–5) to prevent infinite loops

---

## Tech Stack

| Tool | Role |
|---|---|
| LangGraph | Multi-agent graph orchestration |
| Groq (llama-3.3-70b) | LLM for all generation tasks |
| Tavily | Real-time web search |
| Pydantic | Structured LLM outputs |
| Streamlit | Web interface |

---

Built as a portfolio project demonstrating agentic AI system design.
