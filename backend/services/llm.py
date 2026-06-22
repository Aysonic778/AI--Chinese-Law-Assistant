from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI

from backend.config import settings


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str


def get_llm_config() -> LLMConfig:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return LLMConfig(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
        )
    if provider == "qwen":
        return LLMConfig(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            model=settings.qwen_model,
        )
    return LLMConfig(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
    )


def get_llm_client() -> AsyncOpenAI:
    config = get_llm_config()
    if not config.api_key:
        raise ValueError("LLM API key is not configured. Set DEEPSEEK_API_KEY or switch LLM_PROVIDER.")
    return AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)


SYSTEM_PROMPT = """你是法律资料库问答助手。你必须遵守：
1. 只能使用下方「检索到的法律原文」中的内容作答
2. 禁止使用任何外部知识、常识推断或未提供的法条
3. 每个结论必须标注引用来源，格式：[《法律名》第X条]
4. 如果原文不足以回答问题，明确说「资料库中相关条文不足以回答此问题」
5. 禁止联网、禁止编造法条内容或条文编号
6. 回答末尾不要添加免责声明（界面已固定展示）"""


def build_context_block(chunks: list) -> str:
    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        label = chunk.citation_label if hasattr(chunk, "citation_label") else f"《{chunk.law_name}》{chunk.article_number}"
        lines.append(f"[片段{index}] {label}\n{chunk.content}")
    return "\n\n".join(lines)
