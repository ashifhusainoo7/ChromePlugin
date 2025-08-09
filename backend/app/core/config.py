"""
Enterprise Configuration Management
Handles all application configuration with environment variables and validation
"""

import os
from functools import lru_cache
from typing import List, Optional, Union
from pydantic import BaseSettings, validator, EmailStr


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Basic app configuration
    APP_NAME: str = "Google Meet Sentiment Bot"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: Optional[str] = None
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    
    # Redis
    REDIS_URL: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 20
    REDIS_RETRY_ON_TIMEOUT: bool = True
    
    # CORS
    CORS_ORIGINS: str = "*"
    TRUSTED_HOSTS: Optional[str] = None
    
    # Email configuration
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[EmailStr] = None
    MAIL_PORT: int = 587
    MAIL_SERVER: Optional[str] = None
    MAIL_FROM_NAME: Optional[str] = "Meet Sentiment Bot"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    
    # Sentiment Analysis
    SENTIMENT_MODEL: str = "vader"  # vader, textblob, or transformers
    SENTIMENT_THRESHOLD_NEGATIVE: float = -0.1
    SENTIMENT_THRESHOLD_POSITIVE: float = 0.1
    SENTIMENT_ANALYSIS_INTERVAL: int = 5  # seconds
    
    # Audio Processing
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHUNK_SIZE: int = 1024
    AUDIO_FORMAT: str = "wav"
    WHISPER_MODEL: str = "base"  # tiny, base, small, medium, large
    
    # Bot Configuration
    BOT_MAX_INSTANCES: int = 10
    BOT_HEADLESS: bool = True
    BOT_TIMEOUT: int = 300  # seconds
    BOT_RETRY_ATTEMPTS: int = 3
    BOT_RETRY_DELAY: int = 5
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # External APIs
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # File Storage
    UPLOAD_DIR: str = "/tmp/uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: List[str] = ["wav", "mp3", "m4a", "flac"]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Session Management
    SESSION_TIMEOUT: int = 3600  # seconds
    MAX_SESSIONS_PER_USER: int = 5
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v):
        """Validate database URL format"""
        if v and not v.startswith(("postgresql://", "sqlite:///")):
            raise ValueError("Database URL must start with postgresql:// or sqlite:///")
        return v
    
    @validator("REDIS_URL", pre=True)
    def validate_redis_url(cls, v):
        """Validate Redis URL format"""
        if v and not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v
    
    @validator("CORS_ORIGINS")
    def validate_cors_origins(cls, v):
        """Validate CORS origins"""
        if v == "*":
            return v
        # Split and validate each origin
        origins = [origin.strip() for origin in v.split(",")]
        for origin in origins:
            if not origin.startswith(("http://", "https://")) and origin != "localhost":
                raise ValueError(f"Invalid CORS origin: {origin}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("SENTIMENT_MODEL")
    def validate_sentiment_model(cls, v):
        """Validate sentiment analysis model"""
        valid_models = ["vader", "textblob", "transformers"]
        if v not in valid_models:
            raise ValueError(f"Sentiment model must be one of: {valid_models}")
        return v
    
    @validator("WHISPER_MODEL")
    def validate_whisper_model(cls, v):
        """Validate Whisper model size"""
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if v not in valid_models:
            raise ValueError(f"Whisper model must be one of: {valid_models}")
        return v
    
    @validator("UPLOAD_DIR")
    def validate_upload_dir(cls, v):
        """Ensure upload directory exists"""
        os.makedirs(v, exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


class DevSettings(Settings):
    """Development environment settings"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    BOT_HEADLESS: bool = False
    DATABASE_URL: str = "sqlite:///./dev.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000"


class TestSettings(Settings):
    """Test environment settings"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "sqlite:///./test.db"
    REDIS_URL: str = "redis://localhost:6379/1"
    ENABLE_METRICS: bool = False


class ProdSettings(Settings):
    """Production environment settings"""
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    BOT_HEADLESS: bool = True
    ENABLE_METRICS: bool = True
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        """Ensure secret key is set in production"""
        if v == "your-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be set in production")
        return v
    
    @validator("DATABASE_URL")
    def validate_prod_database_url(cls, v):
        """Ensure database URL is set in production"""
        if not v:
            raise ValueError("DATABASE_URL must be set in production")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get application settings based on environment"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "development":
        return DevSettings()
    elif environment == "test":
        return TestSettings()
    elif environment == "production":
        return ProdSettings()
    else:
        return Settings()


# Configuration for different components
def get_database_config() -> dict:
    """Get database configuration"""
    settings = get_settings()
    return {
        "url": settings.DATABASE_URL,
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_timeout": settings.DATABASE_POOL_TIMEOUT
    }


def get_redis_config() -> dict:
    """Get Redis configuration"""
    settings = get_settings()
    return {
        "url": settings.REDIS_URL,
        "max_connections": settings.REDIS_MAX_CONNECTIONS,
        "retry_on_timeout": settings.REDIS_RETRY_ON_TIMEOUT
    }


def get_email_config() -> dict:
    """Get email configuration"""
    settings = get_settings()
    return {
        "username": settings.MAIL_USERNAME,
        "password": settings.MAIL_PASSWORD,
        "from_email": settings.MAIL_FROM,
        "from_name": settings.MAIL_FROM_NAME,
        "port": settings.MAIL_PORT,
        "server": settings.MAIL_SERVER,
        "starttls": settings.MAIL_STARTTLS,
        "ssl_tls": settings.MAIL_SSL_TLS,
        "use_credentials": settings.USE_CREDENTIALS,
        "validate_certs": settings.VALIDATE_CERTS
    }


def get_sentiment_config() -> dict:
    """Get sentiment analysis configuration"""
    settings = get_settings()
    return {
        "model": settings.SENTIMENT_MODEL,
        "threshold_negative": settings.SENTIMENT_THRESHOLD_NEGATIVE,
        "threshold_positive": settings.SENTIMENT_THRESHOLD_POSITIVE,
        "analysis_interval": settings.SENTIMENT_ANALYSIS_INTERVAL
    }


def get_bot_config() -> dict:
    """Get bot configuration"""
    settings = get_settings()
    return {
        "max_instances": settings.BOT_MAX_INSTANCES,
        "headless": settings.BOT_HEADLESS,
        "timeout": settings.BOT_TIMEOUT,
        "retry_attempts": settings.BOT_RETRY_ATTEMPTS,
        "retry_delay": settings.BOT_RETRY_DELAY
    }


def get_audio_config() -> dict:
    """Get audio processing configuration"""
    settings = get_settings()
    return {
        "sample_rate": settings.AUDIO_SAMPLE_RATE,
        "chunk_size": settings.AUDIO_CHUNK_SIZE,
        "format": settings.AUDIO_FORMAT,
        "whisper_model": settings.WHISPER_MODEL
    }