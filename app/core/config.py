from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'ReframeQ Backend'
    env: str = 'development'
    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_algorithm: str = 'HS256'
    jwt_access_token_expire_minutes: int = 60
    ollama_base_url: str = 'http://localhost:11434'
    ollama_model: str = 'mistral'
    ollama_timeout_seconds: int = 60

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


settings = Settings()
