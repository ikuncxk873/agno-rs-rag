import os
from typing import Optional

from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from agno.models.openai import OpenAIChat

from app.config import get_settings
from kb_build import create_knowledge


def create_agent(model_id: Optional[str] = None) -> Agent:
    settings = get_settings()
    os.environ.setdefault("DEEPSEEK_API_KEY", settings.resolved_api_key)
    if settings.gptgod_api_key:
        model = OpenAIChat(
            id=settings.gptgod_model,
            api_key=settings.gptgod_api_key,
            base_url=settings.gptgod_base_url,
        )
    else:
        model = DeepSeek(id=model_id or settings.deepseek_model)
    return Agent(
        name="遥感知识问答助手",
        model=model,
        knowledge=create_knowledge(),
        search_knowledge=True,
        instructions=[
            "你是遥感与地理信息领域的专家，使用中文回答。",
            "回答必须基于知识库内容：先给出结论，再说明依据，并注明信息来源文档名。",
            "如果知识库中没有相关信息，明确说明'知识库中未找到相关信息'，禁止编造。",
        ],
    )
