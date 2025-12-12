import os
from pathlib import Path

class Settings:
    PROJECT_NAME: str = "RecSys"
    
    # Определяем пути относительно этого файла
    BASE_DIR = Path(__file__).resolve().parent
    ROOT_DIR = BASE_DIR.parent
    
    # БД создастся в корне проекта
    DATABASE_URL: str = f"sqlite:///{ROOT_DIR / 'recsys.db'}"

    # Пути к Frontend
    TEMPLATE_DIR = ROOT_DIR / "frontend" / "templates"
    STATIC_DIR = ROOT_DIR / "frontend" / "static"

settings = Settings()