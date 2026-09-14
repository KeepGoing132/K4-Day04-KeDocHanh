from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import (
    ARTIFACTS_DIR,
    ROOT,
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

load_lab_env(ROOT)

st.set_page_config(
    page_title="IT Helpdesk Agent",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ IT Helpdesk Agent — Interactive Console")
st.caption("AI-powered IT Service Desk with Structured Tool Calling & Trace Audit")

# Sidebar Configuration
st.sidebar.header("⚙️ Agent Configuration")

provider_choice = st.sidebar.selectbox(
    "Provider",
    options=["gemini", "openrouter", "openai", "anthropic"],
    index=0,
)

model_override = st.sidebar.text_input(
    "Model Override (Leave blank for default)",
    value="",
    help="Default model will be used if left blank.",
)

version_choice = st.sidebar.selectbox(
    "Artifact Version",
    options=["v3", "v2", "v1", "v0"],
    index=0,
)

history_window = st.sidebar.slider("History Window (turns)", min_value=1, max_value=10, value=5)
max_tool_rounds = st.sidebar.slider("Max Tool Rounds", min_value=1, max_value=8, value=4)

# Load Artifacts
system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
tools_path = ARTIFACTS_DIR / "tools.yaml"

system_prompt = system_prompt_path.read_text(encoding="utf-8") if system_prompt_path.exists() else ""
tool_declarations = load_tool_declarations(tools_path) if tools_path.exists() else []
openai_tools = to_openai_tools(tool_declarations)

artifact_version = build_artifact_version(version_choice, system_prompt_path, tools_path)

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Artifact Integrity")
st.sidebar.code(
    f"Version: {artifact_version.artifact_version}\n"
    f"Prompt: {artifact_version.prompt_hash[:12]}...\n"
    f"Tools:  {artifact_version.tools_hash[:12]}...",
    language="yaml",
)

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []  # Display list of turns

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # History for prompt context: [{"role": ..., "content": ...}]

if "transcript_id" not in st.session_state:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    st.session_state.transcript_id = f"{safe_slug(version_choice)}_{safe_slug(provider_choice)}_{timestamp}"

if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0

if "transcript_turns" not in st.session_state:
    st.session_state.transcript_turns = []

# Action: Clear Chat
if st.sidebar.button("🗑️ Clear Conversation", use_container_width=True):
    st.session_state.messages = []
    st.session_state.chat_history = []
    st.session_state.turn_index = 0
    st.session_state.transcript_turns = []
    st.rerun()

# Display Chat Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tool_events"):
            with st.expander(f"🔍 Inspect Tool Calls ({len(msg['tool_events'])} call(s))", expanded=False):
                for idx, event in enumerate(msg["tool_events"], 1):
                    tool_name = event.get("tool", "unknown")
                    tool_args = event.get("args", {})
                    tool_res = event.get("result", {})
                    has_error = "error" in tool_res or event.get("error")
                    icon = "⚠️" if has_error else "✅"
                    st.markdown(f"**Call #{idx} — `{tool_name}`** {icon}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption("Arguments:")
                        st.json(tool_args)
                    with col2:
                        st.caption("Tool Result:")
                        st.json(tool_res)

# Chat Input & Execution
if prompt := st.chat_input("Nhập câu hỏi hoặc yêu cầu hỗ trợ IT..."):
    # Display user turn
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.turn_index += 1
    selected_model = model_override.strip() or None

    # Prepare messages payload
    messages_payload = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.chat_history, history_window),
        {"role": "user", "content": prompt},
    ]

    turn_record: dict[str, Any] = {
        "turn_index": st.session_state.turn_index,
        "started_at": now_iso(),
        "user": prompt,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        status_placeholder.info("🤖 Processing request and resolving tools...")
        try:
            provider = make_provider(provider_choice)
            result = run_model_tool_loop(
                provider=provider,
                messages=messages_payload,
                tools=openai_tools,
                model=selected_model,
                max_tool_rounds=max_tool_rounds,
            )
            turn_record.update(result)
            assistant_text = result.get("assistant_text", "")
            tool_events = result.get("tool_events", [])

            status_placeholder.empty()
            st.markdown(assistant_text)

            if tool_events:
                with st.expander(f"🔍 Inspect Tool Calls ({len(tool_events)} call(s))", expanded=True):
                    for idx, event in enumerate(tool_events, 1):
                        tool_name = event.get("tool", "unknown")
                        tool_args = event.get("args", {})
                        tool_res = event.get("result", {})
                        has_error = "error" in tool_res or event.get("error")
                        icon = "⚠️" if has_error else "✅"
                        st.markdown(f"**Call #{idx} — `{tool_name}`** {icon}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption("Arguments:")
                            st.json(tool_args)
                        with col2:
                            st.caption("Tool Result:")
                            st.json(tool_res)

            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_text,
                "tool_events": tool_events,
            })
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_text})

        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {str(exc)}"
            status_placeholder.error(f"❌ Error: {err_msg}")
            turn_record.update({"status": "provider_error", "error": err_msg})
            st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Error: {err_msg}"})

        turn_record["ended_at"] = now_iso()
        st.session_state.transcript_turns.append(turn_record)

        # Write transcript file
        transcripts_dir = ROOT / "transcripts"
        transcript_path = transcripts_dir / f"{st.session_state.transcript_id}.transcript.json"
        full_transcript = {
            "transcript_id": st.session_state.transcript_id,
            **artifact_version_dict(artifact_version),
            "provider": provider_choice,
            "model": selected_model or getattr(provider, "default_model", None),
            "system_prompt": str(system_prompt_path),
            "tools": str(tools_path),
            "history_window": history_window,
            "max_tool_rounds": max_tool_rounds,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "turns": st.session_state.transcript_turns,
        }
        write_transcript(transcript_path, full_transcript)

# Sidebar Download Transcript
if st.session_state.transcript_turns:
    st.sidebar.markdown("---")
    st.sidebar.subheader("💾 Export Audit Log")
    transcript_export = json.dumps(
        {
            "transcript_id": st.session_state.transcript_id,
            **artifact_version_dict(artifact_version),
            "turns": st.session_state.transcript_turns,
        },
        ensure_ascii=False,
        indent=2,
    )
    st.sidebar.download_button(
        "📥 Download Transcript JSON",
        data=transcript_export,
        file_name=f"{st.session_state.transcript_id}.json",
        mime="application/json",
        use_container_width=True,
    )
