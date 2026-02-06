"""Application configuration from environment variables."""
from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

class Settings:
    """Application configuration."""
    
    # Server
    APP_NAME: str = os.getenv("APP_NAME", "TrustWise")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://trustwise:trustwise@localhost:5432/trustwise_dev")
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"
    
    # Paths
    CONFIG_DIR: Path = Path(__file__).parent.parent / "config"
    TRUSTED_SOURCES_PATH: Path = CONFIG_DIR / "trusted_sources.json"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/trustwise.log")
    
    # Job timeouts (milliseconds)
    JOB_TIMEOUT_MS: int = int(os.getenv("JOB_TIMEOUT_MS", "30000"))
    TASK_TIMEOUT_MS: int = int(os.getenv("TASK_TIMEOUT_MS", "10000"))

settings = Settings()
