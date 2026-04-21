"""
app.py — AI Research Assistant
Chat-style Streamlit interface with live pipeline progress and HTML download
"""

import streamlit as st
import time

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🔬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"] { display: none; }
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0f0a1e 0%, #1a0f2e 50%, #120a28 100%);
    min-height: 100vh;
}
[data-testid="stAppViewBlockContainer"] {
    padding-top: 0 !important;
    max-width: 780px;
}

/* ── Top nav bar ── */
.top-bar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(15,10,30,0.92);
    backdrop-filter: blur(14px);
    border-bottom: 1px solid rgba(139,92,246,0.2);
    padding: 14px 0 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 24px;
}
.top-bar-icon { font-size: 1.4rem; }
.top-bar-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #ede9fe;
    letter-spacing: 0.02em;
}
.top-bar-sub {
    font-size: 0.78rem;
    color: #7c6fa0;
    margin-left: auto;
}

/* ── Chat bubbles ── */
.msg-row {
    display: flex;
    gap: 12px;
    margin: 18px 0;
    align-items: flex-start;
}
.msg-row.user { flex-direction: row-reverse; }

.avatar {
    width: 34px; height: 34px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
}
.avatar.ai   { background: linear-gradient(135deg,#7c3aed,#a855f7); }
.avatar.user { background: linear-gradient(135deg,#6d28d9,#8b5cf6); }

.bubble {
    max-width: 88%;
    padding: 12px 16px;
    border-radius: 14px;
    font-size: 0.92rem;
    line-height: 1.65;
    word-break: break-word;
}
.bubble.ai {
    background: rgba(30,18,55,0.85);
    border: 1px solid rgba(139,92,246,0.25);
    color: #ddd6fe;
    border-top-left-radius: 4px;
}
.bubble.user {
    background: linear-gradient(135deg,#6d28d9,#7c3aed);
    color: #ffffff;
    border-top-right-radius: 4px;
}

/* ── Step pills ── */
.step-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 500;
    margin: 3px 0;
    width: 100%;
}
.step-pill.done    { background: rgba(167,139,250,.15); color: #c4b5fd; border: 1px solid rgba(167,139,250,.3); }
.step-pill.active  { background: rgba(216,180,254,.18); color: #e9d5ff; border: 1px solid rgba(216,180,254,.4); }
.step-pill.pending { background: rgba(255,255,255,.03); color: #4c4070; border: 1px solid rgba(139,92,246,.12); }
.step-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.step-dot.done    { background: #a78bfa; }
.step-dot.active  { background: #e9d5ff; animation: pulse 1s infinite; }
.step-dot.pending { background: #4c4070; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.25} }

/* ── Paper display ── */
.paper-wrap {
    background: rgba(20,12,40,0.9);
    border: 1px solid rgba(139,92,246,0.22);
    border-radius: 14px;
    padding: 22px 26px;
    color: #ddd6fe;
    font-family: 'Georgia', serif;
    font-size: 0.93rem;
    line-height: 1.85;
    max-height: 480px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    margin-top: 10px;
}
.paper-wrap::-webkit-scrollbar { width: 5px; }
.paper-wrap::-webkit-scrollbar-thumb { background: rgba(139,92,246,.35); border-radius: 4px; }

/* ── Info tag ── */
.info-tag {
    background: rgba(139,92,246,.12);
    border: 1px solid rgba(139,92,246,.3);
    border-radius: 8px;
    padding: 8px 14px;
    color: #c4b5fd;
    font-size: 0.82rem;
    margin: 6px 0;
    line-height: 1.6;
}

/* ── Input area ── */
.input-bar {
    position: fixed;
    bottom: 0; left: 50%;
    transform: translateX(-50%);
    width: 100%; max-width: 780px;
    background: rgba(12,7,24,0.97);
    border-top: 1px solid rgba(139,92,246,0.2);
    padding: 14px 16px 18px;
    z-index: 200;
}
div[data-testid="stTextInput"] input {
    background: rgba(30,18,55,0.9) !important;
    border: 1px solid rgba(139,92,246,0.35) !important;
    border-radius: 24px !important;
    color: #ede9fe !important;
    font-size: 0.95rem !important;
    padding: 12px 20px !important;
    transition: border-color .2s, box-shadow .2s;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #a78bfa !important;
    box-shadow: 0 0 0 3px rgba(139,92,246,.2) !important;
}

/* ── Send button ── */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg,#7c3aed,#a855f7) !important;
    color: white !important;
    border: none !important;
    border-radius: 24px !important;
    padding: 12px 28px !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    height: 47px !important;
    margin-top: 0 !important;
    box-shadow: 0 0 18px rgba(139,92,246,.35) !important;
}
div[data-testid="stButton"] > button:hover { opacity: .88 !important; }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg,#6d28d9,#7c3aed) !important;
    color: white !important;
    border: 1px solid rgba(167,139,250,.4) !important;
    border-radius: 10px !important;
    padding: 10px 22px !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    margin-top: 12px !important;
    width: 100% !important;
}

/* ── Bottom spacer ── */
.bottom-spacer { height: 90px; }

/* ── Welcome screen ── */
.welcome {
    text-align: center;
    padding: 60px 20px 0;
}
.welcome-icon { font-size: 3rem; margin-bottom: 12px; }
.welcome-title {
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(90deg,#c4b5fd,#e9d5ff,#a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
}
.welcome-sub { color: #7c6fa0; font-size: 0.95rem; line-height: 1.6; }
.chip-row { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:22px; }
.chip {
    background: rgba(30,18,55,0.8);
    border: 1px solid rgba(139,92,246,0.25);
    border-radius: 20px;
    padding: 7px 16px;
    color: #a78bfa;
    font-size: 0.82rem;
}
</style>
""", unsafe_allow_html=True)

# ── Late import so CSS renders first ─────────────────────────────────────────
from graph import graph  # noqa

# ── Session state ─────────────────────────────────────────────────────────────
if "messages"   not in st.session_state: st.session_state.messages   = []
if "running"    not in st.session_state: st.session_state.running    = False
if "html_store" not in st.session_state: st.session_state.html_store = {}

# ── Pipeline step definitions ─────────────────────────────────────────────────
STEPS = [
    ("query_generator", "🔍", "Generating search queries"),
    ("webSearch",        "🌐", "Searching the web"),
    ("planner",          "📋", "Planning paper structure"),
    ("writer",           "✍️",  "Writing the paper"),
    ("html_formatter",   "🎨", "Formatting for download"),
]
STEP_IDS = [s[0] for s in STEPS]

# ── Render helpers ────────────────────────────────────────────────────────────

def ai_bubble(content_html: str) -> str:
    return (
        '<div class="msg-row">'
        '<div class="avatar ai">🤖</div>'
        f'<div class="bubble ai">{content_html}</div>'
        '</div>'
    )

def user_bubble(text: str) -> str:
    return (
        '<div class="msg-row user">'
        '<div class="avatar user">👤</div>'
        f'<div class="bubble user">{text}</div>'
        '</div>'
    )

def steps_html(completed: list, current: str | None) -> str:
    out = ""
    for node_id, icon, label in STEPS:
        if node_id in completed:
            cls, dot, badge = "done",    "done",    "✓"
        elif node_id == current:
            cls, dot, badge = "active",  "active",  "…"
        else:
            cls, dot, badge = "pending", "pending", ""
        out += (
            f'<div class="step-pill {cls}">'
            f'<span class="step-dot {dot}"></span>'
            f'{icon} {label}'
            f'<span style="margin-left:auto;font-size:0.78rem">{badge}</span>'
            f'</div>'
        )
    return out

# ── Top nav ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-bar">
  <span class="top-bar-icon">🔬</span>
  <span class="top-bar-title">AI Research Assistant</span>
  <span class="top-bar-sub">LangGraph · Groq · Tavily</span>
</div>
""", unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome">
      <div class="welcome-icon">🔬</div>
      <div class="welcome-title">AI Research Assistant</div>
      <div class="welcome-sub">
        Type any topic below and I'll search the web,<br>
        plan and write a full research paper — ready to download.
      </div>
      <div class="chip-row">
        <span class="chip">🤖 Impact of AI on Healthcare</span>
        <span class="chip">🌍 Climate Change Solutions</span>
        <span class="chip">🧬 CRISPR Gene Editing</span>
        <span class="chip">🚀 Future of Space Exploration</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(user_bubble(msg["content"]), unsafe_allow_html=True)
        elif msg.get("type") == "paper":
            topic_key = msg.get("topic_key", "")
            st.markdown(ai_bubble(msg["content"]), unsafe_allow_html=True)
            st.markdown(f'<div class="paper-wrap">{msg["paper_text"]}</div>', unsafe_allow_html=True)
            if topic_key in st.session_state.html_store:
                st.download_button(
                    label="⬇️  Download Paper as HTML",
                    data=st.session_state.html_store[topic_key],
                    file_name=f"{topic_key[:40].replace(' ','_')}_paper.html",
                    mime="text/html",
                    key=f"dl_{topic_key}",
                )
        else:
            st.markdown(ai_bubble(msg["content"]), unsafe_allow_html=True)

# ── Bottom spacer keeps content above fixed input bar ─────────────────────────
st.markdown('<div class="bottom-spacer"></div>', unsafe_allow_html=True)

# ── Fixed input bar ───────────────────────────────────────────────────────────
st.markdown('<div class="input-bar">', unsafe_allow_html=True)
col_in, col_btn = st.columns([5, 1], gap="small")
with col_in:
    topic = st.text_input(
        "topic",
        placeholder="Ask me to research any topic…",
        label_visibility="collapsed",
        disabled=st.session_state.running,
        key="topic_input",
    )
with col_btn:
    send = st.button("Send", disabled=st.session_state.running, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Run on submit ─────────────────────────────────────────────────────────────
if send and topic.strip():
    st.session_state.running = True
    clean_topic = topic.strip()

    # Persist user message
    st.session_state.messages.append({"role": "user", "content": clean_topic, "type": "text"})
    st.markdown(user_bubble(clean_topic), unsafe_allow_html=True)

    # Live placeholders
    prog_ph     = st.empty()
    paper_ph    = st.empty()
    download_ph = st.empty()

    completed: list[str] = []
    final_paper = ""
    final_html  = ""

    def refresh_progress(extra_html=""):
        next_idx = len(completed)
        cur = STEP_IDS[next_idx] if next_idx < len(STEP_IDS) else None
        prog_ph.markdown(
            ai_bubble(
                '<div style="font-size:0.83rem;color:#7c6fa0;margin-bottom:8px">Working on your research…</div>'
                + steps_html(completed, cur)
                + extra_html
            ),
            unsafe_allow_html=True,
        )

    refresh_progress()  # initial render

    for event in graph.stream({"topic": clean_topic}):
        node_name = list(event.keys())[0]
        node_data = event[node_name]
        extra = ""

        if node_name == "query_generator":
            queries = node_data.get("queries")
            if queries:
                q_text = " · ".join(queries.queries)
                extra = f'<div class="info-tag" style="margin-top:8px">🔍 {q_text}</div>'

        elif node_name == "webSearch":
            wc = len(node_data.get("context", "").split())
            extra = f'<div class="info-tag" style="margin-top:8px">🌐 Gathered ~{wc:,} words from the web.</div>'

        elif node_name == "planner":
            outline = node_data.get("Sections")
            if outline:
                secs = " → ".join(outline.Sections)
                extra = f'<div class="info-tag" style="margin-top:8px">📋 {secs}</div>'

        elif node_name == "writer":
            final_paper = node_data.get("paper", "")
            # Simulate streaming word-by-word
            displayed = ""
            words = final_paper.split()
            for i in range(0, len(words), 10):
                displayed += " ".join(words[i:i+10]) + " "
                paper_ph.markdown(
                    f'<div class="paper-wrap">{displayed}</div>',
                    unsafe_allow_html=True,
                )
                time.sleep(0.03)

        elif node_name == "html_formatter":
            final_html  = node_data.get("html_output", "")
            final_paper = node_data.get("paper", final_paper)

        completed.append(node_name)

        # Show info tag while this step is fresh, then advance progress
        refresh_progress(extra)

    # ── All done ──
    prog_ph.markdown(
        ai_bubble(
            '<div style="color:#a78bfa;font-weight:600;margin-bottom:10px">✅ Research paper is ready!</div>'
            + steps_html(completed, None)
        ),
        unsafe_allow_html=True,
    )

    paper_ph.markdown(
        f'<div class="paper-wrap">{final_paper}</div>',
        unsafe_allow_html=True,
    )

    if final_html:
        st.session_state.html_store[clean_topic] = final_html
        download_ph.download_button(
            label="⬇️  Download Paper as HTML",
            data=final_html,
            file_name=f"{clean_topic[:40].replace(' ','_')}_paper.html",
            mime="text/html",
            key=f"dl_live_{clean_topic}",
        )

    # Persist to history
    st.session_state.messages.append({
        "role":       "assistant",
        "type":       "paper",
        "content":    "✅ Research paper is ready!",
        "paper_text": final_paper,
        "topic_key":  clean_topic,
    })

    st.session_state.running = False
