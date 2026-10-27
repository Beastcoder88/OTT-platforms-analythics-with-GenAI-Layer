import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from ai_layer.text_to_sql import ask

EXAMPLES = [
    "Which subscription tier has the highest churn rate?",
    "How many hours were watched in each region?",
    "How did watch time change month by month?",
    "How much higher was daily watch time during the cricket event than on normal days?",
    "What are the top 3 genres in each region?",
    "How many users signed up in April 2025?",
]

st.set_page_config(page_title="Ask the OTT Data", page_icon="📊", layout="wide")

if "question_text" not in st.session_state:
    st.session_state["question_text"] = ""
if "pending_query" not in st.session_state:
    st.session_state["pending_query"] = None


def format_value(value):
    if pd.api.types.is_number(value):
        value = float(value)
        return f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}"
    return str(value)


def chartable(df):
    return (
        df.shape[1] == 2
        and 2 <= len(df) <= 30
        and pd.api.types.is_numeric_dtype(df.iloc[:, 1])
        and not pd.api.types.is_numeric_dtype(df.iloc[:, 0])
    )


# ---------- Sidebar ----------
st.sidebar.header("Try an example")
for i, example in enumerate(EXAMPLES):
    if st.sidebar.button(example, key=f"example_{i}", use_container_width=True):
        st.session_state["question_text"] = example
        st.session_state["pending_query"] = example
        st.rerun()

st.sidebar.divider()
st.sidebar.caption(
    "The data covers 2025 only, so 'last month' means December 2025. "
    "Answers come from an AI-written SQL query, so check the SQL when a number matters."
)

# ---------- Main page ----------
st.title("Ask the OTT Data")
st.caption("Ask a question in plain English. Case study with simulated data, not affiliated with any streaming company.")

with st.form("ask_form", clear_on_submit=False):
    st.write("**Your question**")
    question_input = st.text_input(
        "Your question",
        value=st.session_state.get("question_text", ""),
        max_chars=300,
        placeholder="e.g. Which region watched the most last month?",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Ask", type="primary")

query_to_run = None
if submitted:
    if question_input.strip():
        query_to_run = question_input.strip()
        st.session_state["question_text"] = query_to_run
    else:
        st.info("Please enter a question.")
elif st.session_state.get("pending_query"):
    query_to_run = st.session_state.pop("pending_query")

if query_to_run:
    with st.spinner("Working on it..."):
        st.session_state["result"] = ask(query_to_run)

result = st.session_state.get("result")
if result:
    st.subheader(result["question"])

    if result.get("is_greeting"):
        st.info(result.get("message", "Hello! How can I help you explore the data?"))
    elif result["error"]:
        (st.info if result["refused"] else st.error)(result["error"])
    else:
        df = result["df"]
        if df is None or df.empty:
            st.warning("The query ran but returned no rows. Try rephrasing; the data covers 2025 only.")
        elif df.shape == (1, 1):
            label = str(df.columns[0]).replace("_", " ").title()
            st.metric(label, format_value(df.iloc[0, 0]))
        else:
            st.dataframe(df, use_container_width=True)
            if chartable(df):
                st.bar_chart(df.set_index(df.columns[0]))
        if result["truncated"]:
            st.caption("Only the first rows are shown.")
        if result["repaired"]:
            st.caption("The first query failed, so the AI corrected it once.")

    if result.get("sql"):
        with st.expander("How this answer was produced (SQL)"):
            st.code(result["sql"], language="sql")
    if result.get("detail") and result.get("error"):
        with st.expander("Technical details"):
            st.code(result["detail"])