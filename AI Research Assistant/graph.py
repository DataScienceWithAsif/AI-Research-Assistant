"""
graph.py — AI Research Assistant Pipeline
LangGraph-based multi-agent research paper generator
"""

import os
from dotenv import load_dotenv
from typing import List
from typing_extensions import TypedDict

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableParallel
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

load_dotenv()

# ─────────────────────────────────────────────
# LLM & Tools Setup
# ─────────────────────────────────────────────

groq_llm = ChatGroq(model="llama-3.3-70b-versatile")
web_search = TavilySearchResults(max_results=2)

# ─────────────────────────────────────────────
# Structured Output Schemas
# ─────────────────────────────────────────────

class Queries(BaseModel):
    queries: List[str] = Field(
        description="3–6 search queries to gather web context for the given research topic"
    )

class Outlines(BaseModel):
    Sections: List[str] = Field(
        description="Main section headings for the research paper"
    )

# ─────────────────────────────────────────────
# Graph State
# ─────────────────────────────────────────────

class GraphState(TypedDict):
    topic: str
    queries: Queries
    context: str
    Sections: Outlines
    paper: str

# ─────────────────────────────────────────────
# LLM Variants with Structured Output
# ─────────────────────────────────────────────

llm_queries     = groq_llm.with_structured_output(Queries)
llm_planning    = groq_llm.with_structured_output(Outlines)

# ─────────────────────────────────────────────
# Node: Query Generator
# ─────────────────────────────────────────────

def query_generator(state: GraphState):
    """Generate 3–6 search queries for the given topic."""
    topic = state["topic"]

    system = (
        "You are an expert at generating precise web search queries. "
        "Given a research topic, produce 3–6 queries that together will surface "
        "the most relevant and up-to-date information needed to write a professional research paper."
    )

    response = llm_queries.invoke([
        SystemMessage(content=system),
        HumanMessage(content=f"Topic: {topic}")
    ])

    return {"queries": response}

# ─────────────────────────────────────────────
# Node: Web Search (parallel)
# ─────────────────────────────────────────────

def _search_one(query: str) -> List[str]:
    """Run a single Tavily search and return result texts."""
    results = web_search.invoke(query)
    return [r["content"] for r in results]


def webSearch(state: GraphState):
    """Run all queries in parallel and merge results into one context string."""
    queries_list = state["queries"].queries

    # Build a RunnableParallel map dynamically from available queries
    tasks = {f"q{i}": (lambda q: lambda _: _search_one(q))(q) for i, q in enumerate(queries_list)}
    parallel = RunnableParallel(**tasks)
    results  = parallel.invoke(queries_list)  # input is unused by lambdas

    all_texts = []
    for key in sorted(results.keys()):
        all_texts.extend(results[key])

    context = "\n\n".join(all_texts)
    return {"context": context}

# ─────────────────────────────────────────────
# Node: Planner
# ─────────────────────────────────────────────

def planner(state: GraphState):
    """Decide the section structure of the research paper."""
    topic   = state["topic"]
    context = state["context"]

    system = (
        "You are a research architect. Based on the topic and web-gathered context, "
        "decide the best section headings for a professional research paper. "
        "Return only the list of section titles — no descriptions."
    )

    response = llm_planning.invoke([
        SystemMessage(content=system),
        HumanMessage(content=f"Topic: {topic}\n\nContext:\n{context}")
    ])

    return {"Sections": response}

# ─────────────────────────────────────────────
# Node: Writer
# ─────────────────────────────────────────────

def writer(state: GraphState):
    """Write the full research paper in Markdown."""
    topic    = state["topic"]
    sections = state["Sections"].Sections
    context  = state["context"]

    system = (
        "You are a professional academic writer. Write a complete, well-structured research paper "
        "in Markdown format using the provided sections and context. "
        "Each section should be thorough, accurate, and flow naturally. "
        "Output ONLY the research paper — no commentary, no preamble."
    )

    response = groq_llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=(
            f"Topic: {topic}\n\n"
            f"Sections: {sections}\n\n"
            f"Context:\n{context}"
        ))
    ])

    return {"paper": response.content}

# ─────────────────────────────────────────────
# Node: HTML Formatter (replaces downable_html)
# ─────────────────────────────────────────────

def html_formatter(state: GraphState):
    """Convert Markdown paper to a styled HTML string stored in state."""
    import re

    paper = state["paper"]

    # Simple Markdown → HTML conversion
    def md_to_html(md: str) -> str:
        lines   = md.split("\n")
        html    = []
        in_ul   = False

        for line in lines:
            # Headings
            if line.startswith("### "):
                if in_ul: html.append("</ul>"); in_ul = False
                html.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("## "):
                if in_ul: html.append("</ul>"); in_ul = False
                html.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("# "):
                if in_ul: html.append("</ul>"); in_ul = False
                html.append(f"<h1>{line[2:]}</h1>")
            # Bullet list
            elif line.startswith("- ") or line.startswith("* "):
                if not in_ul: html.append("<ul>"); in_ul = True
                content = line[2:]
                content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
                html.append(f"  <li>{content}</li>")
            # Blank line
            elif line.strip() == "":
                if in_ul: html.append("</ul>"); in_ul = False
                html.append("")
            # Normal paragraph line
            else:
                if in_ul: html.append("</ul>"); in_ul = False
                line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
                line = re.sub(r"\*(.+?)\*",     r"<em>\1</em>",         line)
                html.append(f"<p>{line}</p>")

        if in_ul:
            html.append("</ul>")

        return "\n".join(html)

    body_html = md_to_html(paper)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Research Paper</title>
  <style>
    /* ── Reset ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Georgia', 'Times New Roman', serif;
      background: #f4f1eb;
      color: #1a1a1a;
      padding: 40px 20px 80px;
      line-height: 1.8;
    }}

    /* ── Paper Card ── */
    .paper {{
      max-width: 860px;
      margin: 0 auto;
      background: #fff;
      border-radius: 4px;
      box-shadow: 0 4px 30px rgba(0,0,0,0.12);
      padding: 60px 70px;
    }}

    /* ── Typography ── */
    h1 {{
      font-size: 2rem;
      font-weight: 700;
      color: #111;
      border-bottom: 3px solid #2563eb;
      padding-bottom: 12px;
      margin-bottom: 28px;
    }}
    h2 {{
      font-size: 1.35rem;
      font-weight: 700;
      color: #1d4ed8;
      margin: 36px 0 10px;
    }}
    h3 {{
      font-size: 1.1rem;
      font-weight: 600;
      color: #374151;
      margin: 24px 0 8px;
    }}
    p {{
      margin: 10px 0;
      font-size: 1rem;
      text-align: justify;
    }}
    ul {{
      margin: 10px 0 10px 24px;
    }}
    li {{
      margin: 4px 0;
    }}
    strong {{ color: #111; }}

    /* ── Footer Meta ── */
    .meta {{
      text-align: center;
      font-size: 0.8rem;
      color: #9ca3af;
      margin-top: 50px;
      border-top: 1px solid #e5e7eb;
      padding-top: 16px;
    }}

    @media (max-width: 640px) {{
      .paper {{ padding: 30px 22px; }}
      h1 {{ font-size: 1.5rem; }}
    }}
  </style>
</head>
<body>
  <div class="paper">
    {body_html}
    <div class="meta">Generated by AI Research Assistant &bull; Powered by LangGraph + Groq</div>
  </div>
</body>
</html>"""

    return {"paper": paper, "html_output": full_html}

# ─────────────────────────────────────────────
# Build & Compile Graph
# ─────────────────────────────────────────────

class ExtendedState(GraphState, total=False):
    html_output: str


def build_graph():
    builder = StateGraph(ExtendedState)

    builder.add_node("query_generator", query_generator)
    builder.add_node("webSearch",       webSearch)
    builder.add_node("planner",         planner)
    builder.add_node("writer",          writer)
    builder.add_node("html_formatter",  html_formatter)

    builder.add_edge(START,             "query_generator")
    builder.add_edge("query_generator", "webSearch")
    builder.add_edge("webSearch",       "planner")
    builder.add_edge("planner",         "writer")
    builder.add_edge("writer",          "html_formatter")
    builder.add_edge("html_formatter",  END)

    return builder.compile()


graph = build_graph()
