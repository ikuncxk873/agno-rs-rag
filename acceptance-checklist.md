# 客户视角验收清单

以客户视角逐条验收,发现 bug 即记录并修复。每次交付前重跑。

| # | 场景 | 预期 | 实测 | 状态 |
|---|------|------|------|------|
| 1 | 空输入点发送 | 前端禁用发送,后端 400 | API 400 ✓;前端禁用 ✓(Playwright) | ✓ |
| 2 | 超长输入(>20000 字符) | 后端 400,前端不崩溃 | pytest 400 ✓;Docker 实测 400 ✓ | ✓ |
| 3 | 回答中重复点击发送 | 按钮禁用,不产生并发请求 | 按钮禁用 ✓ + delta 渲染 ✓(Playwright) | ✓ |
| 4 | 回答中断网 | 显示错误条,页面不白屏 | 错误条 "Failed to fetch" ✓(Playwright) | ✓ |
| 5 | 重启服务后查看会话 | 会话与消息全部保留 | Docker 重启后会话保留 ✓ | ✓ |
| 6 | 上传非法文件(.exe) | 400,提示仅支持 txt/md/pdf | pytest ✓;Docker 实测 400 ✓ | ✓ |
| 7 | 上传新文档后提问 | 重建完成,新文档内容可被问答命中 | 上传→入库 ✓;Docker 实测命中 ✓(sources 5 个真实文档) | ✓ |
| 8 | 错误 ACCESS_TOKEN | 401,前端弹回登录页 | API 401 ✓;前端登录流程 ✓(Playwright) | ✓ |
| 9 | 删除会话 | 会话消失,消息级联删除 | Docker 删除 ✓(级联由 pytest 覆盖) | ✓ |
| 10 | 上游 API 余额不足 | 错误条显示,不白屏不卡死 | SSE error 事件 ✓;前端错误条 ✓(Playwright) | ✓ |
| 11 | 切换 DEEPSEEK_MODEL 后提问 | 回答正常,消息 model 字段记录新模型 | 宿主实测 ✓;Docker 内实测 ✓(deepseek-v4-flash,delta 358) | ✓ |

## Docker 验收记录(2026-08-13)

**结论**:镜像构建 ✓ / 容器启动 ✓ / 健康检查 ✓ / 知识库自动重建 ✓ / 持久化 ✓ / 鉴权 ✓ / SSE 协议 ✓ / 浏览器 14/14 项通过 ✓ / **LLM 问答全链路 ✓**(DeepSeek key)

**本次发现并修复**:
1. **向量残留 — agno LanceDb.delete() 是空实现** — rebuild 时旧向量永不清理,已删除文档(huge.txt 2098 行)仍被检索到。kb_build.py 加 `_reset_vector_db()`,用 lancedb 原生 drop_table 清空后重建;API 触发 rebuild 验证 rows 2104 → 5,提问 sources 只剩真实文档
2. **ACCESS_TOKEN 为空时鉴权静默放行** — 容器内 `access_token=""` → `require_token` 直接 return。已生成随机 token 写入 `.env`
2. **openai 未锁版本** — Docker 装到 3.0.0(重写版)与 agno 2.8.7 不兼容,流式超时;锁定 `openai==2.48.0`(宿主实测版本)
3. **容器内直连 LLM API 被墙** — compose 注入 `HTTP(S)_PROXY=http://host.docker.internal:7892`(走 Windows VPN 出网),并覆盖 NO_PROXY 防 config.py setdefault 拦截
4. **嵌入模型预缓存失效** — fastembed 0.8.0 每次加载联网校验,xet 路径被墙后 fallback 重下 90MB(~80s/次)。`scripts/precache_embedder.py` 构建时用 resolve URL 补齐 HF 缓存 → local_files_only 命中 → rebuild 1m24s → 32s,下载报错归零

**环境修复**:
- docker.io 直连被墙 → `~/.docker/daemon.json` 加 registry-mirrors(daocloud/1ms)
- 宿主 Docker 无 WSL 发行版 → Docker Desktop 自动建内部发行版,无需装 Ubuntu

**浏览器验收脚本**: `e2e/docker_accept.mjs`(Playwright + Edge headless,需 npm 安装过 playwright),重跑: `cd e2e && node docker_accept.mjs <ACCESS_TOKEN>`

## 已修复记录

| 日期 | 场景 | 问题 | 修复 |
|------|------|------|------|
| 2026-08-13 | #7 | agno LanceDb.delete() 是空实现,rebuild 后旧向量残留 | kb_build.py 用 lancedb 原生 drop_table 清空再重建 |
| 2026-08-13 | #10 | agno 余额不足时产出 RunErrorEvent 而非抛异常,error 事件缺失 | stream_answer 捕获 RunErrorEvent 并转为 error 事件 |
| 2026-08-13 | #1 等 | httpx 读取 Windows 注册表系统代理(farmerCore),对 api.deepseek.com 隧道中断 | config.py 设置 NO_PROXY 绕过注册表代理 |
