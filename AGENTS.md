# 开发流程说明

## gstack（仅开发阶段）

编码前建议运行 `/plan-ceo-review` 审核产品方案。Phase 1 完成后可用 `/qa`、`/ship` 验收。

**禁止**将 gstack 的 `/browse` 或任何联网 skill 接入产品问答链路。

## 产品红线

- 回答只能基于资料库检索到的法律原文
- 禁止 LLM 联网搜索或使用外部知识补全
- 禁止使用 `deepseek-reasoner`（DeepSeek-R1）
- 查不到足够依据时必须拒答或软拒答

## Docker 启动

```bash
cp .env.example .env
docker compose up --build
```

## 架构要点

- 两阶段 Law Router：法律摘要路由 → 法条检索
- Reranker：`BAAI/bge-reranker-large`
- 四层防幻觉：检索门槛、Prompt 约束、引用校验、摘录兜底
- 多轮对话：`conversation_id` + `GET /api/chat/conversations`

## 本地启动

```bash
# 后端
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python scripts/import_laws.py
uvicorn backend.main:app --reload --port 8000

# 前端
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

访问 http://localhost:3000
