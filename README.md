# 遥感知识问答 Agent（Agno + DeepSeek RAG）

基于 Agno 框架的遥感领域知识问答应用：本地向量库 + DeepSeek V4 Flash 模型，
回答引用知识库文档并标注来源。

> 作品集项目：遥感规范/论文知识库 RAG，可替换 `knowledge/` 语料扩展。

## 架构

```
knowledge/*.txt ──▶ FastEmbedEmbedder(bge-small-zh-v1.5, 本地嵌入)
                        │
                        ▼
                    LanceDb 向量库 (data/lancedb)
                        │
                        ▼
Agent(DeepSeek V4 Flash) ──▶ Streamlit 问答界面（流式输出 + 引用来源）
```

- 嵌入走本地 ONNX（fastembed），零 API 成本
- 检索用 Agno Knowledge + LanceDb（余弦相似度，top-5）
- 模型走 DeepSeek API（V4 Flash，thinking 模式）

## 快速开始

```bash
pip install -r requirements.txt

# API Key（复用已有环境变量，未设置时读取 ANTHROPIC_AUTH_TOKEN）
set DEEPSEEK_API_KEY=your_key

# 1. 构建知识库（首次运行自动下载嵌入模型，约 100MB）
python kb_build.py

# 2. 启动问答界面
streamlit run app.py
```

## 目录结构

| 文件 | 作用 |
|------|------|
| `knowledge/` | 语料库（.txt/.md/.pdf 均可，加文件后重建知识库） |
| `kb_build.py` | 构建/重建向量库 |
| `agent_core.py` | Agent 工厂（模型 + 知识库 + 指令） |
| `app.py` | Streamlit 问答界面 |
| `data/lancedb/` | 向量库（构建生成） |

## 扩展方向

- 换语料：把真实 GB/T 规范、论文 PDF 放入 `knowledge/` 后重建
- 换模型：`agent_core.py` 中改 `DeepSeek(id="...")` 或换成 agno 支持的其他 provider
- 加引用格式：调整 `agent_core.py` 的 instructions 控制输出格式
