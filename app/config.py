import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# farmerCore 把系统代理写入 Windows 注册表,httpx 默认读取后隧道中断,直连必须绕过
os.environ.setdefault("NO_PROXY", "api.deepseek.com,api.gptgod.online")

PROJECT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "遥感知识问答"
    deepseek_api_key: str = ""
    anthropic_auth_token: str = ""
    deepseek_model: str = "deepseek-v4-flash"
    gptgod_api_key: str = ""
    gptgod_model: str = "gpt-5.6-luna"
    gptgod_base_url: str = "https://api.gptgod.online/v1"
    access_token: str = ""
    knowledge_dir: Path = PROJECT_DIR / "knowledge"
    lancedb_dir: Path = PROJECT_DIR / "data" / "lancedb"
    sqlite_path: Path = PROJECT_DIR / "data" / "app.db"
    max_results: int = 5
    max_input_chars: int = 20000
    upload_exts: tuple = (".txt", ".md", ".pdf")

    @property
    def resolved_api_key(self) -> str:
        return self.gptgod_api_key or self.deepseek_api_key or self.anthropic_auth_token

    @property
    def resolved_model(self) -> str:
        return self.gptgod_model if self.gptgod_api_key else self.deepseek_model


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
