import os

from agno.agent import Agent
from agno.models.deepseek import DeepSeek

from kb_build import create_knowledge


def create_agent() -> Agent:
    os.environ.setdefault("DEEPSEEK_API_KEY", os.environ.get("ANTHROPIC_AUTH_TOKEN", ""))
    return Agent(
        name="遥感知识问答助手",
        model=DeepSeek(id="deepseek-v4-flash"),
        knowledge=create_knowledge(),
        search_knowledge=True,
        instructions=[
            "你是遥感与地理信息领域的专家，使用中文回答。",
            "回答必须基于知识库内容：先给出结论，再说明依据，并注明信息来源文档名。",
            "如果知识库中没有相关信息，明确说明'知识库中未找到相关信息'，禁止编造。",
        ],
    )
