from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
import os, time, re
from typing import List, Generator
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# ⚡ Model & Tools Setup
# ──────────────────────────────────────────────
groq_llm = ChatGroq(
    model="llama-3.3-70b-versatile", 
    temperature=0.3,
    max_tokens=1000,
    timeout=30,  # 30-second timeout
    max_retries=2
)
web_search = TavilySearchResults(max_results=3)

class GraphState(TypedDict):
    query: str
    optimized_query: str
    search_results: List[str]
    context: str
    answer: str
    sources: List[str]

# ──────────────────────────────────────────────
# 🔹 Nodes
# ──────────────────────────────────────────────
def optimize_query(state: GraphState):
    try:
        query_text = state.get("query") or "latest AI trends"
        response = groq_llm.invoke([
            SystemMessage(content="Rewrite the user query into a highly precise search query."),
            HumanMessage(content=query_text)
        ])
        return {"optimized_query": response.content.strip()}
    except Exception as e:
        print(f"Optimization Error: {e}")
        # Fallback so the graph continues even if LLM fails
        return {"optimized_query": state.get("query")}

def web_search_node(state: GraphState):
    # Using both the optimized and original query for broader coverage
    queries = [state["optimized_query"], f"{state['query']} latest developments"]
    merged = []
    for q in queries:
        try:
            results = web_search.invoke(q)
            merged.extend([r["content"] for r in results if r.get("content")])
        except Exception:
            continue
    return {"search_results": merged[:8]}

def compress_context(state: GraphState):
    results = state.get("search_results", [])
    context = "\n---\n".join(results)
    return {"context": context[:4000]} # Stay within LLM context limits

def generate_answer(state: GraphState):
    response = groq_llm.invoke([
        SystemMessage(content="""You are a Lead AI Researcher. 
        Provide a deep-dive technical report with:
        - Professional bullet points
        - Clear, bold headings
        - A concise conclusion
        Keep it between 400-600 words."""),
        HumanMessage(content=f"Query: {state['query']}\n\nContext: {state['context']}")
    ])
    return {
        "answer": response.content, 
        "sources": state.get("search_results", [])[:3]
    }

# ──────────────────────────────────────────────
# 🧾 HTML Generator Helper
# ──────────────────────────────────────────────
def convert_to_html(answer: str, query: str, sources: List[str]) -> str:
    # Clean up the answer text for HTML rendering
    formatted_answer = answer.replace("\n", "<br>")
    
    source_list = "".join([f"<li>{s[:150]}...</li>" for s in sources])
    
    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: auto; padding: 20px; background-color: #f4f7f6; }}
            .container {{ background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .content {{ margin-top: 20px; }}
            .sources {{ margin-top: 30px; background: #ecf0f1; padding: 20px; border-radius: 5px; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Research Report: {query}</h1>
            <div class="content">{formatted_answer}</div>
            <div class="sources">
                <h3>Sources Consulted</h3>
                <ul>{source_list}</ul>
            </div>
        </div>
    </body>
    </html>
    """

# ──────────────────────────────────────────────
# 🧠 Graph Construction
# ──────────────────────────────────────────────
builder = StateGraph(GraphState)
builder.add_node("optimize", optimize_query)
builder.add_node("search", web_search_node)
builder.add_node("compress", compress_context)
builder.add_node("answer", generate_answer)

builder.add_edge(START, "optimize")
builder.add_edge("optimize", "search")
builder.add_edge("search", "compress")
builder.add_edge("compress", "answer")
builder.add_edge("answer", END)

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

# ──────────────────────────────────────────────
# 📡 Streaming Engine
# ──────────────────────────────────────────────
NODE_LABELS = {
    "optimize": "🔍 Refining Research Strategy...",
    "search": "🌐 Scanning Global Databases...",
    "compress": "📚 Synthesizing Knowledge...",
    "answer": "✍️ Authoring Final Report..."
}

def run_graph_streaming(query: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    
    # 🌟 CRITICAL: Yield a heartbeat immediately
    yield {"type": "node", "node": "start", "label": "🚀 Dispatching Agents...", "data": {}}
    
    try:
        # Pass the initial state
        for event in graph.stream({"query": query}, config=config, stream_mode="updates"):
            if not event or not isinstance(event, dict):
                continue
            
            node = list(event.keys())[0]
            data = event[node]

            if isinstance(data, dict):
                yield {
                    "type": "node",
                    "node": node,
                    "label": NODE_LABELS.get(node, node),
                    "data": data
                }
        
        # ── Final Extraction (The fix for the 'str' object error) ──
        state_snapshot = graph.get_state(config)
        
        # We access the dictionary of state variables using .values
        final_values = state_snapshot.values if hasattr(state_snapshot, 'values') else {}

        if final_values.get("answer"):
            html_content = convert_to_html(
                final_values["answer"],
                final_values.get("query", query),
                final_values.get("sources", [])
            )

            yield {
                "type": "done",
                "answer": final_values["answer"],
                "sources": final_values.get("sources", []),
                "html": html_content
            }
            
    except Exception as e:
        print(f"Graph Streaming Error: {e}")
        raise e