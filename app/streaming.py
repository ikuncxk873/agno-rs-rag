import json
from typing import Any, AsyncIterator, Optional

from agno.agent import Agent

SEARCH_TOOL = "search_knowledge_base"


def _parse_docs(content: Any) -> list:
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (TypeError, ValueError):
            return []
    if isinstance(content, dict):
        return [content]
    if isinstance(content, list):
        return content
    return []


def _doc_name(doc: Any) -> Optional[str]:
    if not isinstance(doc, dict):
        return None
    for key in ("name", "file_name", "path"):
        value = doc.get(key)
        if value:
            return str(value)
    return None


def extract_sources(output: Any) -> list[str]:
    sources = []
    for message in getattr(output, "messages", None) or []:
        if getattr(message, "role", "") != "tool":
            continue
        if getattr(message, "tool_name", "") != SEARCH_TOOL:
            continue
        for doc in _parse_docs(getattr(message, "content", None)):
            name = _doc_name(doc)
            if name and name not in sources:
                sources.append(name)
    return sources


async def stream_answer(agent: Agent, question: str) -> AsyncIterator[dict]:
    error_message = None
    try:
        async for item in agent.arun(question, stream=True, stream_events=True, yield_run_output=True):
            if getattr(item, "messages", None):
                yield {"type": "sources", "names": extract_sources(item)}
                continue
            name = type(item).__name__
            if name == "RunErrorEvent":
                error_message = getattr(item, "content", None) or "未知错误"
                continue
            if name == "RunContentEvent":
                content = getattr(item, "content", None)
                if isinstance(content, str) and content:
                    yield {"type": "delta", "text": content}
    except Exception as exc:
        error_message = f"回答失败:{exc}"
    if error_message:
        yield {"type": "error", "message": str(error_message)}
    yield {"type": "done"}


def encode_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
