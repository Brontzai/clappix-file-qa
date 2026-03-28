"""
Настройки бота и правила QA проверки.
Все параметры из .env — легко менять под проект.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "./credentials.json")

# Правила проверки креативов
# Меняем под проект — у каждого клиента свои требованя
MIN_WIDTH = int(os.getenv("MIN_WIDTH", "1920"))
MIN_HEIGHT = int(os.getenv("MIN_HEIGHT", "1080"))
MAX_DURATION_SEC = int(os.getenv("MAX_DURATION_SEC", "30"))
ALLOWED_FORMATS = os.getenv("ALLOWED_FORMATS", "mp4").split(",")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "40"))

# Временная папка для скачаных файлов
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/file-qa")
