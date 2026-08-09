import asyncio
import json
import sys
from pathlib import Path

import streamlit as st

# Python 3.9: agno 导入时创建 asyncio.Lock 需要事件循环，Streamlit 脚本线程默认没有
asyncio.set_event_loop(asyncio.new_event_loop())

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from agent_core import create_agent
from kb_build import KNOWLEDGE_DIR

st.set_page_config(page_title="遥感知识问答", layout="centered")


@st.cache_resource
def get_agent():
    return create_agent()


def extract_sources(output) -> list[str]:
    sources = []
    for message in getattr(output, "messages", None) or []:
        if getattr(message, "role", "") != "tool":
            continue
        if getattr(message, "tool_name", "") != "search_knowledge_base":
            continue
        try:
            docs = json.loads(message.content)
        except (TypeError, ValueError):
            continue
        for doc in docs:
            name = doc.get("name")
            if name and name not in sources:
                sources.append(name)
    return sources


def stream_answer(agent, question, placeholder):
    text = ""
    final_output = None
    for item in agent.run(
        question, stream=True, stream_events=True, yield_run_output=True
    ):
        if getattr(item, "messages", None):
            final_output = item
            continue
        content = getattr(item, "content", None)
        if content and isinstance(content, str):
            text += content
            placeholder.markdown(text)
    placeholder.markdown(text)
    return text, final_output


def main() -> None:
    st.title("遥感知识问答")
    st.caption("Agno + DeepSeek + 本地嵌入（bge-small-zh）")

    with st.sidebar:
        st.header("知识库")
        files = sorted(p.name for p in KNOWLEDGE_DIR.iterdir() if p.is_file())
        st.write(f"语料 {len(files)} 个文件")
        for name in files:
            st.caption(f"· {name}")
        if st.button("重建知识库"):
            from kb_build import rebuild

            with st.spinner("重建中..."):
                rebuild()
            st.success("重建完成")
            get_agent.clear()
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("citations"):
                st.caption("来源：" + "、".join(message["citations"]))

    question = st.chat_input("问我关于遥感规范、NDVI、三北监测的问题…")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        agent = get_agent()
        with st.chat_message("assistant"):
            placeholder = st.empty()
            answer, output = stream_answer(agent, question, placeholder)
            sources = extract_sources(output)
            if sources:
                st.markdown("**引用来源：**")
                for name in sources:
                    st.caption(f"- {name}")

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "citations": sources}
        )


if __name__ == "__main__":
    main()
