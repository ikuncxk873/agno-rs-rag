# 遥感知识问答 · 可部署全栈 RAG 应用

遥感领域私有知识库问答系统:FastAPI 后端 + 原生 JS 前端 + 本地向量检索 + DeepSeek 模型,`docker compose up` 一键部署。

> 作品集项目 / 知识库定制接单模板。替换 `knowledge/` 语料即可交付任意行业(律所合同、企业规范等)。

## 架构

```
knowledge/*.txt/.md/.pdf
        │  FastEmbedEmbedder(bge-small-zh-v1.5, 本地 ONNX, 零 API 成本)
        ▼
   LanceDB(data/lancedb)  ←── 向量检索 top-5
        │
        ▼
   Agno Agent ── DeepSeek V4 Flash / Pro(SSE 流式)
        │
        ▼
   FastAPI /api/* ── 原生 JS 单页(static/)
        │
   SQLite(data/app.db)── 会话与消息持久化
```

## 快速开始

### Docker(推荐)

```bash
cp .env.example .env   # 填入 API Key 与 ACCESS_TOKEN
docker compose up --build
```

打开 http://localhost:8002 ,输入 ACCESS_TOKEN 登录。首次启动自动构建向量库,重启数据不丢。

### 本地开发

```bash
pip install -r requirements-dev.txt
python kb_build.py               # 构建向量库(首次)
uvicorn app.main:app --port 8001 # 端口 8000 常被 C-Lodop 占用
pytest tests/ -q                 # 测试
```

Streamlit 旧版界面(`app.py`)保留为开发调试工具,生产入口是 FastAPI。

## 配置(.env)

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key(未设置时回退 `ANTHROPIC_AUTH_TOKEN`) |
| `DEEPSEEK_MODEL` | 模型 ID:默认 `deepseek-v4-flash`,可切 `deepseek-v4-pro` |
| `ACCESS_TOKEN` | 访问令牌,非空时所有 /api 请求需 Bearer 认证 |
| `GPTGOD_API_KEY` 等 | 可选:GPTGod 中转接口(OpenAI 兼容),设置后优先使用 |

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查(无认证) |
| POST | `/api/chat` | 提问,SSE 流式:delta / sources / error / done |
| GET/POST | `/api/sessions` | 会话列表 / 新建 |
| GET | `/api/sessions/{id}/messages` | 会话消息 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| GET/POST | `/api/documents` | 文档列表 / 上传(txt/md/pdf,自动重建) |
| POST | `/api/rebuild` | 手动重建向量库 |

## 模型选择

- **deepseek-v4-flash**:默认,便宜快速,日常问答
- **deepseek-v4-pro**:1M 上下文 + 强 Agent 能力,复杂分析;改 `.env` 的 `DEEPSEEK_MODEL` 一行切换

## 验收清单

见 [acceptance-checklist.md](acceptance-checklist.md)。
