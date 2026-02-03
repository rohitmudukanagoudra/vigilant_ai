"""Configuration management for the analysis agent system."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    
    # Model Configuration
    llm_provider: str = Field(default="gemini", env="LLM_PROVIDER")
    cli_command: list[str] = Field(default=["gemini", "query"], env="CLI_COMMAND")
    gemini_model: str = Field(default="gemini-1.5-flash-latest", env="GEMINI_MODEL")
    gemini_vision_model: str = Field(default="gemini-1.5-flash-latest", env="GEMINI_VISION_MODEL")
    
    # Video Processing
    frame_extraction_interval: int = Field(default=2, env="FRAME_EXTRACTION_INTERVAL")
    max_frames_per_video: int = Field(default=50, env="MAX_FRAMES_PER_VIDEO")
    
    # OCR Settings
    ocr_languages: str = Field(default="en", env="OCR_LANGUAGES")
    ocr_confidence_threshold: float = Field(default=0.3, env="OCR_CONFIDENCE_THRESHOLD")
    
    # Vision Analysis
    vision_max_concurrent: int = Field(default=3, env="VISION_MAX_CONCURRENT")
    vision_batch_size: int = Field(default=5, env="VISION_BATCH_SIZE")
    vision_analyze_all_frames: bool = Field(default=True, env="VISION_ANALYZE_ALL_FRAMES")
    
    # Agent Configuration
    agent_temperature: float = Field(default=0.1, env="AGENT_TEMPERATURE")
    agent_max_retries: int = Field(default=3, env="AGENT_MAX_RETRIES")
    
    # FastAPI Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # Streamlit Configuration
    streamlit_port: int = Field(default=8501, env="STREAMLIT_PORT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()