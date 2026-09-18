"""Streamlit UI for the tool-use reasoning agent.

Usage:
    streamlit run app.py

Wires the existing retriever/, agent/, apis/, and eval/ modules to a
browser UI: ask a question, watch the ReAct or DFSDT reasoning trace
unfold step by step, compare both strategies side by side, and browse
the results of the last benchmark run.
"""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .main .block-container { padding-top: 2rem; max-width: 1100px; }

    h1 { font-weight: 700; letter-spacing: -0.02em; }
    .subtitle { color: #6b7280; font-size: 1rem; margin-top: -0.6rem; margin-bottom: 1.5rem; }

    .api-badge {
        display: inline-block;
        background: #eef2ff;
        color: #3730a3;
        border: 1px solid #c7d2fe;
        border-radius: 999px;
        padding: 3px 12px;
        margin: 3px 4px 3px 0;
        font-size: 0.82rem;
        font-weight: 500;
    }

    .strategy-badge {
        display: inline-block;
        background: #f0fdf4;
        color: #166534;
        border: 1px solid #bbf7d0;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .retry-badge {
        display: inline-block;
        background: #fff7ed;
        color: #9a3412;
        border: 1px solid #fed7aa;
        border-radius: 6px;
        padding: 1px 8px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-left: 8px;
    }

    .final-answer-box {
        background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
        border: 1px solid #86efac;
        border-radius: 12px;
        padding: 1.1rem 1.4rem;
        margin: 0.8rem 0 1.2rem 0;
    }
    .final-answer-box .label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #16a34a;
        margin-bottom: 0.3rem;
    }
    .final-answer-box .text { font-size: 1.05rem; color: #14532d; line-height: 1.5; }

    .error-box {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        color: #991b1b;
    }

    .step-card {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.6rem;
        background: #fafafa;
    }
    .step-card .thought { color: #374151; margin-bottom: 0.4rem; }
    .step-card .action { color: #1d4ed8; font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.88rem; margin-bottom: 0.4rem; }
    .step-card .observation { color: #059669; font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.85rem; white-space: pre-wrap; }

    .metric-row { display: flex; gap: 1rem; margin: 0.6rem 0 1rem 0; }

    section[data-testid="stSidebar"] .stMarkdown p { margin-bottom: 0.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

EXAMPLE_QUESTIONS = [
    "What's the weather in Tokyo and convert 20 USD to EUR",
    "Find a quote about perseverance and today's top news headline",
    "What is the capital of Japan and define the word 'serendipity'",
]

STEP_ICONS = ["🟦", "🟩", "🟨", "🟧", "🟪", "🟥", "⬜", "⬛"]


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
        status.update(label="Done", state="complete")
        return result, candidate_apis, elapsed, api_calls
    except Exception as exc:  # noqa: BLE001 - surfaced as a friendly UI message, not a crash
        status.update(label="Failed", state="error")
        st.markdown(f'<div class="error-box">⚠️ {friendly_error(exc)}</div>', unsafe_allow_html=True)
        return None


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def render_api_badges(apis: list) -> None:
    badges = "".join(f'<span class="api-badge">{api.name}</span>' for api in apis)
    st.markdown(badges, unsafe_allow_html=True)


def render_final_answer(result) -> None:
    answer = result.answer or "The agent did not produce a final answer within its step budget."
    st.markdown(
        f'<div class="final-answer-box"><div class="label">Final Answer</div>'
        f'<div class="text">{answer}</div></div>',
        unsafe_allow_html=True,
    )


def render_trace(result, strategy: str) -> None:
    steps = result.steps
    retried = strategy == "DFSDT" and getattr(result, "explored_paths", 0) > len(steps)

    with st.expander(f"Reasoning trace ({len(steps)} steps)", expanded=True):
        if retried:
            st.markdown(
                f'<span class="retry-badge">↩ backtracked — explored {result.explored_paths} '
                f'branch attempts to reach {len(steps)} steps</span>',
                unsafe_allow_html=True,
            )
            st.write("")

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

            obs_html = (
                f'<div class="observation">👁️ Observation: {step.observation}</div>'
                if step.observation is not None
                else ""
            )
            action_html = f'<div class="action">⚙️ {action_part}</div>' if action_part else ""
            thought_html = f'<div class="thought">💭 {thought_part}</div>' if thought_part else ""

            st.markdown(
                f'<div class="step-card">'
                f'<b>{icon} Step {i + 1}</b><br/>'
                f"{thought_html}{action_html}{obs_html}"
                f"</div>",
                unsafe_allow_html=True,
            )


def render_result(result, apis: list, elapsed: float, api_calls: int, strategy: str) -> None:
    st.markdown(f'<span class="strategy-badge">{strategy}</span>', unsafe_allow_html=True)
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
    st.header("Configuration")
    strategy = st.selectbox("Agent strategy", ["ReAct", "DFSDT"], index=0)
    top_k = st.slider("APIs to retrieve", min_value=1, max_value=9, value=5)

    st.divider()
    st.subheader("Available APIs")
    for api in get_registry().all():
        st.markdown(f"**{api.name}**  \n<span style='color:#6b7280;font-size:0.85rem'>{api.description}</span>", unsafe_allow_html=True)

    st.divider()
    with st.expander("View project architecture"):
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

st.title("Tool-Use Reasoning Agent")
st.markdown(
    '<div class="subtitle">A ReAct / DFSDT agent that retrieves relevant APIs '
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
    for col, example in zip(ex_cols, EXAMPLE_QUESTIONS):
        if col.button(example, key=f"ex_{example}", width="stretch"):
            st.session_state.question = example
            st.rerun()

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
                st.subheader("ReAct")
                with st.status("Starting ReAct...", expanded=True) as status_r:
                    outcome_r = run_agent(q, "ReAct", top_k, status_r)
                if outcome_r:
                    render_result(*outcome_r, strategy="ReAct")

            with col_dfsdt:
                st.subheader("DFSDT")
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
        st.image(chart_path, caption="Pass rate comparison: ReAct vs DFSDT", width="stretch")
    else:
        st.info("No pass_rate_comparison.png found in results/ yet.")

    if os.path.exists(csv_path):
        with st.expander("Raw benchmark results"):
            st.dataframe(pd.read_csv(csv_path), width="stretch")
