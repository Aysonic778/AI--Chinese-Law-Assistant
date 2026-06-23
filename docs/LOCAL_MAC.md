# macOS + Cursor 本地开发指南

## 环境要求

| 工具 | 版本 |
|---|---|
| Python | **3.10+**（推荐 3.12，不要用系统自带的 3.9.6） |
| Node.js | 18+（你当前 v22.17.1 ✅） |
| npm | 任意较新（你当前 10.9.2 ✅） |
| Homebrew | 已安装 ✅ |

## 一、Homebrew PATH（若 `brew` 找不到）

```bash
eval "$(/opt/homebrew/bin/brew shellenv)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
```

## 二、安装 Python 3.12

```bash
brew install python@3.12
python3.12 --version   # 应显示 3.12.x
```

## 三、克隆项目

```bash
cd ~/Projects
git clone https://github.com/Aysonic778/AI--Chinese-Law-Assistant.git
cd AI--Chinese-Law-Assistant
git checkout cursor/law-assistant-mvp-0579
```

## 四、首次配置（只需一次）

在 **Cursor → Terminal → New Terminal** 中执行：

```bash
cd ~/Projects/AI--Chinese-Law-Assistant

python3.12 -m venv .venv
source .venv/bin/activate
python --version          # 确认是 3.12.x

pip install -r backend/requirements.txt

cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=sk-...

python scripts/import_laws.py

cd frontend
cp .env.local.example .env.local
npm install
cd ..
```

`.env` 最少配置：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的密钥
```

`frontend/.env.local` 保持：

```env
NEXT_PUBLIC_API_URL=
BACKEND_URL=http://127.0.0.1:8000
```

## 五、用 Cursor 打开项目

1. **File → Open Folder**
2. 选择 `AI--Chinese-Law-Assistant`
3. 点击 **Trust**

## 六、日常启动（两个终端）

**终端 1 — 后端：**

```bash
cd ~/Projects/AI--Chinese-Law-Assistant
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

**终端 2 — 前端：**

```bash
cd ~/Projects/AI--Chinese-Law-Assistant/frontend
npm run dev
```

浏览器打开：

- 对话：http://localhost:3000
- 资料库：http://localhost:3000/library

## 七、自检

```bash
curl http://localhost:8000/api/health
curl http://localhost:3000/api/library
```

## 八、常见问题

| 问题 | 解决 |
|---|---|
| `brew: command not found` | 执行第二节 PATH 配置 |
| `python` 仍是 3.9.6 | 用 `python3.12 -m venv .venv` 并 `source .venv/bin/activate` |
| HuggingFace 下载慢/失败 | `export HF_ENDPOINT=https://hf-mirror.com` 后重试 `import_laws.py` |
| 页面能开但 AI 不回答 | 检查 `.env` 中的 `DEEPSEEK_API_KEY` |
| 端口占用 | `lsof -i :3000` 或 `lsof -i :8000`，`kill -9 <PID>` |

## 九、可选：gstack 开发流程

```bash
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.cursor/skills/gstack
cd ~/.cursor/skills/gstack && ./setup --host cursor
```

在 Cursor Chat 可使用 `/plan-ceo-review`、`/qa`、`/ship` 等。
