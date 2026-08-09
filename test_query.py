import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from agent_core import create_agent

agent = create_agent()
resp = agent.run("NDVI 的计算公式是什么？有哪些注意事项？")

print("=== 回答 ===")
print(resp.content)
print("=== 引用 ===")
citations = getattr(resp, "citations", None)
if citations:
    print("raw:", citations.raw)
    docs = getattr(citations, "documents", None)
    if docs:
        for doc in docs:
            print("doc:", doc)
else:
    print("无引用信息")
