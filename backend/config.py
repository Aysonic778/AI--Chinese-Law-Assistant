from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-max"

    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_device: str = "cpu"

    min_relevance_score: float = 0.35
    llm_temperature: float = 0.05
    retrieval_top_k: int = 8
    soft_refusal_top_k: int = 3

    chroma_persist_dir: str = "./data/chroma"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    upload_dir: str = "./data/uploads"
    laws_dir: str = "./data/laws"

    cors_origins: str = "http://localhost:3000"


settings = Settings()
