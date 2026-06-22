# 法律资料库可信问答

专为中国法律场景设计的 **「引用或拒答」** 式资料库问答 Web 应用。只从你指定的法律资料库作答，每条结论可追溯到具体法条；查不到足够依据时会拒答，并展示最接近的条文摘录。

## 功能（MVP）

- 预置 5 部核心法律（宪法、刑法、公司法、税收征收管理法、劳动法）
- 按「第 X 条」智能分块入库
- 单阶段向量检索 + 强制法条引用
- 软拒答（附最接近条文摘录）
- Chat 对话页（SSE 流式输出）
- 禁止联网、禁止外源知识

## 技术栈

- 前端：Next.js 15 + TypeScript + Tailwind
- 后端：FastAPI + SQLite + ChromaDB
- Embedding：`BAAI/bge-small-zh-v1.5`
- LLM：Qwen-Max / DeepSeek-V3（可配置，禁用 R1）

## 快速开始

### 1. 环境配置

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 或其他 LLM API Key
```

### 2. 后端

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python scripts/import_laws.py
uvicorn backend.main:app --reload --port 8000
```

### 3. 前端

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

打开 http://localhost:3000

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET | `/api/library` | 资料库法律列表 |
| GET | `/api/library/citations/{chunk_id}` | 查看引用原文 |
| POST | `/api/chat` | 单轮问答（JSON） |
| POST | `/api/chat/stream` | 单轮问答（SSE） |

## 免责声明

本系统生成的内容仅供参考，不构成法律意见。重要决策请咨询执业律师。

## 文档

- [产品规格书](docs/SPEC.md)
- [开发说明](AGENTS.md)
