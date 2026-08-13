# -*- coding: utf-8 -*-
"""预缓存嵌入模型:补齐 HF 缓存结构,使 fastembed 走 local_files_only 命中,零联网加载。

背景:fastembed 0.8.0 每次加载都先联网 model_info + snapshot_download,
hf-mirror API 可达但 huggingface_hub 的 xet 下载路径不可用,导致每次都
fallback 到 GCS 重新下载 54.6MB 模型(~80s)。本脚本在构建时用 resolve URL
直下补齐所有文件到 HF 缓存,运行时 snapshot_download(local_files_only=True)
直接命中,不再联网。
"""
import os
import urllib.request

from huggingface_hub import RepoFile, list_repo_tree, model_info

REPO = "Qdrant/bge-small-zh-v1.5"
CACHE = "/app/cache/fastembed"
BASE = f"https://hf-mirror.com/{REPO}/resolve/main"

sha = model_info(REPO).sha
snap = f"{CACHE}/models--{REPO.replace('/', '--')}/snapshots/{sha}"
os.makedirs(snap, exist_ok=True)

files = [f.path for f in list_repo_tree(REPO, repo_type="model") if isinstance(f, RepoFile)]
missing = []
for rel in files:
    dst = f"{snap}/{rel}"
    if os.path.exists(dst):
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        urllib.request.urlretrieve(f"{BASE}/{rel}", dst)
    except Exception as exc:
        missing.append((rel, str(exc)[:80]))

refs = f"{CACHE}/models--{REPO.replace('/', '--')}/refs"
os.makedirs(refs, exist_ok=True)
open(f"{refs}/main", "w").write(sha)

if missing:
    raise SystemExit(f"预缓存不完整,缺失: {missing}")
print(f"预缓存完成: {len(files)} 个文件, sha={sha[:12]}")
