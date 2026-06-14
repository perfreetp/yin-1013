from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    APP_NAME: str = "路面执法协同后端服务"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_PORT: int = 8000

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/traffic_enforcement"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    JWT_SECRET_KEY: str = "default-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    STORAGE_PATH: str = "./storage"
    MAX_FILE_SIZE: int = 52428800
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/avi", "video/mov"]

    TRAFFIC_API_BASE_URL: str = "https://api.traffic.gov.cn"
    VEHICLE_INFO_API_URL: str = "https://api.vehicle.gov.cn"
    CONGESTION_API_URL: str = "https://api.congestion.gov.cn"
    OCR_SERVICE_URL: str = "http://localhost:5000/ocr"

    SCHOOL_ZONE_RADIUS_METERS: int = 200
    HOSPITAL_ZONE_RADIUS_METERS: int = 300
    PEAK_HOUR_MORNING_START: str = "07:00"
    PEAK_HOUR_MORNING_END: str = "09:00"
    PEAK_HOUR_EVENING_START: str = "17:00"
    PEAK_HOUR_EVENING_END: str = "19:00"


settings = Settings()
