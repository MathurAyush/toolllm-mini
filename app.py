"""Streamlit UI for the tool-use reasoning agent.

Usage:
    streamlit run app.py

Wires the existing retriever/, agent/, apis/, and eval/ modules to a
browser UI: ask a question, watch the ReAct or DFSDT reasoning trace
unfold step by step, compare both strategies side by side, and browse
the results of the last benchmark run.
"""

from __future__ import annotations

import base64
import html
import os
import time

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agent.dfsdt import DFSDTAgent, DFSDTResult
from agent.llm import BaseLLM
from agent.react import ReActAgent, ReActResult
from apis.registry import keyless_registry
from retriever.retriever import APIRetriever

st.set_page_config(
    page_title="Tool-Use Reasoning Agent",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CUSTOM THEME — futuristic / cyberpunk styling, injected as one <style> block.
# Edit colors via the CSS variables under :root; section comments below mark
# where each visual feature (background, title, cards, timeline, etc.) lives.
# =============================================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --tl-bg: #0a0e17;
        --tl-blue: #00d9ff;
        --tl-purple: #a855f7;
        --tl-pink: #ec4899;
        --tl-amber: #f59e0b;
        --tl-text: #e5e7eb;
        --tl-text-dim: #94a3b8;
    }

    /* ---- Base layout ---- */
    .main .block-container { padding-top: 2rem; max-width: 1200px; }
    html, body, [class*="css"] { color: var(--tl-text); }

    /* ---- Animated background: slow-drifting neon glow ---- */
    .stApp {
        background:
            radial-gradient(circle at 15% 20%, rgba(0, 217, 255, 0.10), transparent 42%),
            radial-gradient(circle at 85% 15%, rgba(168, 85, 247, 0.10), transparent 42%),
            radial-gradient(circle at 50% 85%, rgba(236, 72, 153, 0.07), transparent 55%),
            var(--tl-bg);
        background-size: 200% 200%;
        animation: tl-bg-shift 26s ease-in-out infinite alternate;
    }
    @keyframes tl-bg-shift {
        0% { background-position: 0% 0%; }
        100% { background-position: 100% 100%; }
    }

    /* ---- Title / header ---- */
    .tl-header-wrap { display: flex; align-items: center; gap: 0.7rem; margin-top: 0.4rem; }
    .tl-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 2.5rem;
        font-weight: 900;
        letter-spacing: 0.01em;
        margin: 0;
        background: linear-gradient(90deg, var(--tl-blue), var(--tl-purple), var(--tl-pink), var(--tl-blue));
        background-size: 300% 100%;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        animation: tl-gradient-shift 6s ease infinite;
    }
    @keyframes tl-gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .tl-live-dot {
        width: 11px; height: 11px; border-radius: 50%; flex-shrink: 0;
        background: #00ff9c;
        box-shadow: 0 0 8px #00ff9c, 0 0 18px #00ff9c;
        animation: tl-pulse 1.6s ease-in-out infinite;
    }
    @keyframes tl-pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.5); opacity: 0.55; }
    }
    .tl-subtitle {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--tl-text-dim);
        font-size: 1rem;
        margin: 0.2rem 0 1.6rem 0;
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1220 0%, #0a0e17 100%);
        border-right: 1px solid rgba(0, 217, 255, 0.25);
        box-shadow: 6px 0 30px rgba(0, 217, 255, 0.06);
    }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--tl-blue);
    }
    .tl-api-item {
        display: flex; gap: 0.55rem; align-items: flex-start;
        padding: 0.4rem 0; border-bottom: 1px dashed rgba(255, 255, 255, 0.07);
    }
    .tl-api-icon { font-size: 1.15rem; line-height: 1.4; }
    .tl-api-name { font-family: 'JetBrains Mono', monospace; color: var(--tl-blue); font-weight: 600; font-size: 0.85rem; }
    .tl-api-desc { color: var(--tl-text-dim); font-size: 0.78rem; line-height: 1.3; }

    /* ---- Buttons (Run, Compare, example pills) ---- */
    div[data-testid="stButton"] button {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.10), rgba(168, 85, 247, 0.10));
        border: 1px solid rgba(0, 217, 255, 0.4);
        color: var(--tl-text);
        border-radius: 999px;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        padding: 0.5rem 1.1rem;
        transition: all 0.3s ease;
    }
    div[data-testid="stButton"] button:hover {
        transform: translateY(-2px) scale(1.03);
        border-color: var(--tl-blue);
        box-shadow: 0 0 18px rgba(0, 217, 255, 0.55), 0 0 34px rgba(168, 85, 247, 0.28);
        color: #ffffff;
    }
    button[kind="primary"] {
        background: linear-gradient(135deg, var(--tl-blue), var(--tl-purple)) !important;
        border: none !important;
        color: #04070d !important;
        font-weight: 700 !important;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 0 24px rgba(0, 217, 255, 0.75), 0 0 44px rgba(236, 72, 153, 0.4) !important;
    }

    /* ---- Tabs ---- */
    button[data-baseweb="tab"] { font-family: 'Space Grotesk', sans-serif; color: var(--tl-text-dim); }
    button[data-baseweb="tab"][aria-selected="true"] { color: var(--tl-blue) !important; }
    div[data-baseweb="tab-highlight"] {
        background: linear-gradient(90deg, var(--tl-blue), var(--tl-purple), var(--tl-pink)) !important;
        height: 3px !important;
        box-shadow: 0 0 10px var(--tl-blue);
    }

    /* ---- Expander / status containers ---- */
    div[data-testid="stExpander"] {
        border: 1px solid rgba(0, 217, 255, 0.25) !important;
        border-radius: 14px !important;
        background: rgba(255, 255, 255, 0.02) !important;
    }
    div[data-testid="stStatusWidget"] {
        border: 1px solid rgba(0, 217, 255, 0.3) !important;
        border-radius: 14px !important;
        background: rgba(0, 217, 255, 0.03) !important;
    }

    /* ---- Metrics ---- */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.6rem 0.8rem;
    }
    div[data-testid="stMetricLabel"] { color: var(--tl-text-dim) !important; font-family: 'Space Grotesk', sans-serif !important; }
    div[data-testid="stMetricValue"] { color: var(--tl-blue) !important; font-family: 'JetBrains Mono', monospace !important; }

    /* ---- API / strategy badges ---- */
    .tl-api-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(0, 217, 255, 0.35);
        color: #7dd3fc;
        border-radius: 999px;
        padding: 3px 12px;
        margin: 3px 5px 3px 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
    }
    .tl-strategy-badge {
        display: inline-block;
        padding: 0.28rem 0.95rem;
        border-radius: 999px;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 0.78rem;
        letter-spacing: 0.04em;
    }
    .tl-strategy-react { background: rgba(0, 217, 255, 0.12); border: 1px solid var(--tl-blue); color: var(--tl-blue); box-shadow: 0 0 12px rgba(0, 217, 255, 0.35); }
    .tl-strategy-dfsdt { background: rgba(168, 85, 247, 0.12); border: 1px solid var(--tl-purple); color: var(--tl-purple); box-shadow: 0 0 12px rgba(168, 85, 247, 0.35); }

    /* ---- Compare-tab column headers ---- */
    .tl-compare-header {
        display: flex; align-items: center; gap: 0.5rem;
        font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 1.15rem;
        padding: 0.6rem 1rem; border-radius: 12px; margin-bottom: 0.7rem;
    }
    .tl-compare-header.react { background: linear-gradient(90deg, rgba(0, 217, 255, 0.15), transparent); border-left: 4px solid var(--tl-blue); color: var(--tl-blue); }
    .tl-compare-header.dfsdt { background: linear-gradient(90deg, rgba(168, 85, 247, 0.15), transparent); border-left: 4px solid var(--tl-purple); color: var(--tl-purple); }

    /* ---- Final answer: glassmorphism pop-in card ---- */
    .tl-final {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.10), rgba(168, 85, 247, 0.12), rgba(236, 72, 153, 0.08));
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 217, 255, 0.5);
        border-radius: 16px;
        padding: 1.3rem 1.6rem;
        margin: 0.9rem 0 1.3rem 0;
        box-shadow: 0 0 24px rgba(0, 217, 255, 0.25), 0 0 48px rgba(168, 85, 247, 0.15);
        animation: tl-pop-in 0.5s cubic-bezier(.2, .9, .3, 1.3);
    }
    @keyframes tl-pop-in {
        from { opacity: 0; transform: scale(0.9); }
        to { opacity: 1; transform: scale(1); }
    }
    .tl-final-label {
        font-family: 'Space Grotesk', sans-serif; font-size: 0.75rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.08em; color: var(--tl-blue);
        margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.4rem;
    }
    .tl-final-text { font-size: 1.08rem; color: #f5f3ff; line-height: 1.6; font-family: 'Space Grotesk', sans-serif; word-break: break-word; }

    /* ---- Error box ---- */
    .tl-error { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.5); color: #fecaca; border-radius: 12px; padding: 1rem 1.3rem; }

    /* ---- Reasoning timeline ---- */
    .tl-timeline { position: relative; padding-left: 1.7rem; margin-top: 0.5rem; }
    .tl-timeline::before {
        content: ""; position: absolute; left: 0.55rem; top: 0.4rem; bottom: 0.4rem; width: 2px;
        background: linear-gradient(180deg, var(--tl-blue), var(--tl-purple), var(--tl-pink));
        opacity: 0.5;
    }
    .tl-step {
        position: relative;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
        opacity: 0;
        animation: tl-fade-slide 0.5s ease forwards;
    }
    .tl-step-dot {
        position: absolute; left: -1.62rem; top: 1.15rem; width: 10px; height: 10px; border-radius: 50%;
        background: var(--tl-blue); box-shadow: 0 0 8px var(--tl-blue);
    }
    @keyframes tl-fade-slide {
        from { opacity: 0; transform: translateY(14px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .tl-step-title { font-family: 'JetBrains Mono', monospace; color: #ffffff; font-weight: 600; margin-bottom: 0.55rem; font-size: 0.92rem; }
    .tl-line { border-radius: 6px; padding: 0.5rem 0.7rem; margin-bottom: 0.4rem; font-size: 0.85rem; line-height: 1.55; word-break: break-word; }
    .tl-thought { border-left: 3px solid var(--tl-blue); background: rgba(0, 217, 255, 0.06); color: #cdefff; }
    .tl-action { border-left: 3px solid var(--tl-purple); background: rgba(168, 85, 247, 0.08); color: #e9d5ff; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; }
    .tl-observation { border-left: 3px solid var(--tl-pink); background: rgba(236, 72, 153, 0.07); color: #fbcfe8; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; white-space: pre-wrap; }

    /* ---- DFSDT backtrack badge: pulsing amber warning ---- */
    .tl-retry-badge {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.6); color: #fbbf24;
        padding: 0.35rem 0.85rem; border-radius: 999px; font-size: 0.78rem; font-weight: 600;
        animation: tl-amber-pulse 1.8s ease-in-out infinite;
    }
    @keyframes tl-amber-pulse {
        0%, 100% { box-shadow: 0 0 6px rgba(245, 158, 11, 0.4); }
        50% { box-shadow: 0 0 20px rgba(245, 158, 11, 0.95); }
    }

    /* ---- Custom "thinking" loader (replaces the default spinner) ---- */
    .tl-loader-wrap { display: flex; align-items: center; gap: 0.9rem; padding: 0.6rem 0.2rem; }
    .tl-loader-ring {
        width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
        background: conic-gradient(var(--tl-blue), var(--tl-purple), var(--tl-pink), var(--tl-blue));
        -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 5px), #000 calc(100% - 5px));
        mask: radial-gradient(farthest-side, transparent calc(100% - 5px), #000 calc(100% - 5px));
        animation: tl-spin 1s linear infinite;
    }
    @keyframes tl-spin { to { transform: rotate(360deg); } }
    .tl-loader-text { font-family: 'Space Grotesk', sans-serif; color: var(--tl-text-dim); font-size: 0.88rem; }

    /* ---- Results Dashboard: table + chart card ---- */
    .stMarkdown table {
        width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 12px;
        overflow: hidden; border: 1px solid rgba(0, 217, 255, 0.25); font-family: 'Space Grotesk', sans-serif;
    }
    .stMarkdown table th {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.2), rgba(168, 85, 247, 0.2));
        color: #ffffff; padding: 0.6rem 0.9rem; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.03em;
    }
    .stMarkdown table td { padding: 0.55rem 0.9rem; font-size: 0.88rem; color: var(--tl-text-dim); border-top: 1px solid rgba(255, 255, 255, 0.06); }
    .stMarkdown table tr:nth-child(even) td { background: rgba(0, 217, 255, 0.045); }
    .stMarkdown table tr:hover td { background: rgba(168, 85, 247, 0.10); color: #ffffff; }

    .tl-chart-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(0, 217, 255, 0.3);
        border-radius: 16px;
        padding: 1rem;
        box-shadow: 0 0 22px rgba(0, 217, 255, 0.12);
        margin: 0.6rem 0 1rem 0;
    }
    .tl-chart-card img { width: 100%; border-radius: 10px; display: block; }

    /* ---- Responsive tweaks ---- */
    @media (max-width: 900px) {
        .tl-title { font-size: 1.7rem; }
        .main .block-container { padding-left: 1rem; padding-right: 1rem; }
        .tl-compare-header { font-size: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

EXAMPLE_QUESTIONS = [
    ("🌤️", "What's the weather in Tokyo and convert 20 USD to EUR"),
    ("💬", "Find a quote about perseverance and today's top news headline"),
    ("🌍", "What is the capital of Japan and define the word 'serendipity'"),
]

STEP_ICONS = ["🟦", "🟩", "🟨", "🟧", "🟪", "🟥", "⬜", "⬛"]

API_ICONS = {
    "calculator": "🧮",
    "weather": "🌤️",
    "search": "🔍",
    "currency_exchange": "💱",
    "wikipedia_summary": "📚",
    "joke": "😂",
    "random_quote": "💬",
    "dictionary": "📖",
    "country_info": "🌍",
    "openweathermap": "⛅",
    "news_headlines": "📰",
}

LOADER_HTML = """
<div class="tl-loader-wrap">
  <div class="tl-loader-ring"></div>
  <div class="tl-loader-text">Neural reasoning in progress…</div>
</div>
"""


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def get_registry():
    return keyless_registry()


@st.cache_resource(show_spinner=False)
def get_retriever(_registry):
    return APIRetriever(apis=_registry.all())


def build_llm() -> BaseLLM:
    provider = os.environ.get("BENCHMARK_PROVIDER", "gemini")
    if provider == "anthropic":
        from agent.anthropic_llm import AnthropicLLM

        return AnthropicLLM(model=os.environ.get("BENCHMARK_MODEL", "claude-haiku-4-5-20251001"))
    if provider == "gemini":
        from agent.gemini_llm import GeminiLLM

        return GeminiLLM(model=os.environ.get("BENCHMARK_MODEL", "gemini-3.5-flash-lite"))
    raise ValueError(f"Unknown BENCHMARK_PROVIDER '{provider}' (expected 'anthropic' or 'gemini').")


def _select_example(text: str) -> None:
    st.session_state.question = text


def friendly_error(exc: Exception) -> str:
    message = str(exc)
    lower = message.lower()
    if "rate limit" in lower or "429" in message:
        return "The model provider is rate-limiting requests right now. Wait a moment and try again."
    if "timeout" in lower or "timed out" in lower:
        return "The request to the model or an API timed out. Please try again."
    if "api key" in lower or "credential" in lower:
        return "Missing or invalid API credentials. Check your .env file (GEMINI_API_KEY / ANTHROPIC_API_KEY)."
    return f"Something went wrong while running the agent: {message}"


# ---------------------------------------------------------------------------
# Agent execution with live status updates
# ---------------------------------------------------------------------------


def run_agent(instruction: str, strategy: str, top_k: int, status) -> tuple[object, list, float, int] | None:
    """Runs retrieval + the chosen agent, updating `status` as it goes.

    Returns (result, candidate_apis, elapsed_seconds, api_call_count) or
    None if an error occurred (a friendly message is shown instead).
    """
    loader = st.empty()
    loader.markdown(LOADER_HTML, unsafe_allow_html=True)
    try:
        status.update(label="Retrieving relevant APIs...", state="running")
        registry = get_registry()
        retriever = get_retriever(registry)
        candidate_apis = [r.api for r in retriever.retrieve(instruction, top_k=top_k)]

        status.update(label=f"Reasoning with {strategy}...", state="running")
        llm = build_llm()
        start = time.time()

        if strategy == "DFSDT":
            agent = DFSDTAgent(registry=registry, llm=llm)
        else:
            agent = ReActAgent(registry=registry, llm=llm)

        result = agent.run(instruction, candidate_apis=candidate_apis)
        elapsed = time.time() - start

        api_calls = sum(1 for step in result.steps if step.observation is not None)
        loader.empty()
        status.update(label="Done", state="complete")
        return result, candidate_apis, elapsed, api_calls
    except Exception as exc:  # noqa: BLE001 - surfaced as a friendly UI message, not a crash
        loader.empty()
        status.update(label="Failed", state="error")
        st.markdown(f'<div class="tl-error">⚠️ {html.escape(friendly_error(exc))}</div>', unsafe_allow_html=True)
        return None


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def render_api_badges(apis: list) -> None:
    badges = "".join(
        f'<span class="tl-api-badge">{API_ICONS.get(api.name, "🔧")} {html.escape(api.name)}</span>'
        for api in apis
    )
    st.markdown(badges, unsafe_allow_html=True)


def render_final_answer(result) -> None:
    answer = result.answer or "The agent did not produce a final answer within its step budget."
    st.markdown(
        f'<div class="tl-final"><div class="tl-final-label">✨ Final Answer</div>'
        f'<div class="tl-final-text">{html.escape(answer)}</div></div>',
        unsafe_allow_html=True,
    )


def render_trace(result, strategy: str) -> None:
    steps = result.steps
    retried = strategy == "DFSDT" and getattr(result, "explored_paths", 0) > len(steps)

    with st.expander(f"Reasoning trace ({len(steps)} steps)", expanded=True):
        html_parts: list[str] = []

        if retried:
            html_parts.append(
                f'<div class="tl-retry-badge">🔀 Backtracked — explored {result.explored_paths} '
                f'branch attempts to reach {len(steps)} steps</div><div style="height:0.6rem"></div>'
            )

        html_parts.append('<div class="tl-timeline">')
        for i, step in enumerate(steps):
            icon = STEP_ICONS[i % len(STEP_ICONS)]
            text = step.thought_or_action.strip()

            thought_part, action_part = text, ""
            if "Action:" in text:
                idx = text.index("Action:")
                thought_part, action_part = text[:idx].strip(), text[idx:].strip()
            elif "Finish[" in text:
                idx = text.index("Finish[")
                thought_part, action_part = text[:idx].strip(), text[idx:].strip()

            lines = ""
            if thought_part:
                lines += f'<div class="tl-line tl-thought">💭 {html.escape(thought_part)}</div>'
            if action_part:
                lines += f'<div class="tl-line tl-action">⚙️ {html.escape(action_part)}</div>'
            if step.observation is not None:
                lines += f'<div class="tl-line tl-observation">👁️ Observation: {html.escape(str(step.observation))}</div>'

            delay = i * 0.12
            html_parts.append(
                f'<div class="tl-step" style="animation-delay:{delay:.2f}s">'
                f'<span class="tl-step-dot"></span>'
                f'<div class="tl-step-title">{icon} Step {i + 1}</div>'
                f"{lines}"
                f"</div>"
            )
        html_parts.append("</div>")

        st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_result(result, apis: list, elapsed: float, api_calls: int, strategy: str) -> None:
    badge_class = "tl-strategy-react" if strategy == "ReAct" else "tl-strategy-dfsdt"
    st.markdown(f'<span class="tl-strategy-badge {badge_class}">{strategy}</span>', unsafe_allow_html=True)
    st.write("")
    render_final_answer(result)

    st.caption("Retrieved APIs")
    render_api_badges(apis)

    c1, c2, c3 = st.columns(3)
    c1.metric("API calls made", api_calls)
    c2.metric("Time taken", f"{elapsed:.1f}s")
    c3.metric("Reasoning steps", len(result.steps))

    render_trace(result, strategy)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Configuration")
    strategy = st.selectbox("Agent strategy", ["ReAct", "DFSDT"], index=0)
    top_k = st.slider("APIs to retrieve", min_value=1, max_value=9, value=5)

    st.divider()
    st.subheader("🧰 Available APIs")
    for api in get_registry().all():
        icon = API_ICONS.get(api.name, "🔧")
        st.markdown(
            f'<div class="tl-api-item"><span class="tl-api-icon">{icon}</span>'
            f'<div><div class="tl-api-name">{html.escape(api.name)}</div>'
            f'<div class="tl-api-desc">{html.escape(api.description)}</div></div></div>',
            unsafe_allow_html=True,
        )

    st.divider()
    with st.expander("🗺️ View project architecture"):
        st.markdown(
            """
**Retriever** — embeds the question and every registered API's
name/description (TF-IDF or sentence-transformer), then ranks APIs
by similarity and passes the top-k candidates forward.

**Agent** — a ReAct or DFSDT loop drives Thought → Action →
Observation steps against the candidate APIs using an LLM backend
(Anthropic or Gemini), until it emits a final answer or exhausts its
step budget. DFSDT additionally branches and backtracks over
alternative actions.

**Evaluator** — an LLM-as-judge scores each run's final answer
against the expected outcome (pass/fail with rationale), and a
win-rate comparator aggregates ReAct vs. DFSDT results into the
benchmark tables and charts shown in the Results Dashboard tab.
            """
        )

# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="tl-header-wrap"><span class="tl-live-dot"></span>'
    '<h1 class="tl-title">Tool-Use Reasoning Agent</h1></div>'
    '<div class="tl-subtitle">A ReAct / DFSDT agent that retrieves relevant APIs '
    "from a tool pool and reasons over them, following the ToolLLM approach "
    "to API retrieval and multi-step tool use.</div>",
    unsafe_allow_html=True,
)

if "question" not in st.session_state:
    st.session_state.question = ""

tab_run, tab_compare, tab_dashboard = st.tabs(["Run Agent", "Compare ReAct vs DFSDT", "Results Dashboard"])

# --- Tab 1: single-strategy run ---------------------------------------------

with tab_run:
    st.text_input("Ask a question", key="question", placeholder="e.g. What's the weather in Tokyo?")

    st.caption("Try an example:")
    ex_cols = st.columns(len(EXAMPLE_QUESTIONS))
    for col, (icon, example) in zip(ex_cols, EXAMPLE_QUESTIONS):
        col.button(
            f"{icon}  {example}",
            key=f"ex_{example}",
            width="stretch",
            on_click=_select_example,
            args=(example,),
        )

    run_clicked = st.button("Run", type="primary")

    if run_clicked:
        question = st.session_state.question.strip()
        if not question:
            st.warning("Please enter a question first.")
        else:
            with st.status("Starting...", expanded=True) as status:
                outcome = run_agent(question, strategy, top_k, status)
            if outcome:
                result, apis, elapsed, api_calls = outcome
                render_result(result, apis, elapsed, api_calls, strategy)

# --- Tab 2: side-by-side comparison -----------------------------------------

with tab_compare:
    st.write("Run the same question through both strategies and compare their traces directly.")
    compare_question = st.text_input(
        "Question", key="compare_question", placeholder="e.g. Convert 20 USD to EUR and define 'serendipity'"
    )
    compare_clicked = st.button("Run Comparison", type="primary")

    if compare_clicked:
        q = compare_question.strip()
        if not q:
            st.warning("Please enter a question first.")
        else:
            col_react, col_dfsdt = st.columns(2)

            with col_react:
                st.markdown('<div class="tl-compare-header react">⚛️ ReAct</div>', unsafe_allow_html=True)
                with st.status("Starting ReAct...", expanded=True) as status_r:
                    outcome_r = run_agent(q, "ReAct", top_k, status_r)
                if outcome_r:
                    render_result(*outcome_r, strategy="ReAct")

            with col_dfsdt:
                st.markdown('<div class="tl-compare-header dfsdt">🌌 DFSDT</div>', unsafe_allow_html=True)
                with st.status("Starting DFSDT...", expanded=True) as status_d:
                    outcome_d = run_agent(q, "DFSDT", top_k, status_d)
                if outcome_d:
                    render_result(*outcome_d, strategy="DFSDT")

# --- Tab 3: benchmark results dashboard -------------------------------------

with tab_dashboard:
    st.write("Results from the last benchmark run (`scripts/run_benchmark.py`), loaded without re-running anything.")

    results_dir = os.path.join(os.path.dirname(__file__), "results")
    table_path = os.path.join(results_dir, "comparison_table.md")
    chart_path = os.path.join(results_dir, "pass_rate_comparison.png")
    csv_path = os.path.join(results_dir, "benchmark_results.csv")

    if os.path.exists(table_path):
        with open(table_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("No comparison_table.md found in results/ yet — run the benchmark first.")

    if os.path.exists(chart_path):
        with open(chart_path, "rb") as f:
            chart_b64 = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(
            f'<div class="tl-chart-card"><img src="data:image/png;base64,{chart_b64}" '
            f'alt="Pass rate comparison: ReAct vs DFSDT"/></div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No pass_rate_comparison.png found in results/ yet.")

    if os.path.exists(csv_path):
        with st.expander("Raw benchmark results"):
            st.dataframe(pd.read_csv(csv_path), width="stretch")
