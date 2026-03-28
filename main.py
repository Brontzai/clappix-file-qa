"""
File QA Bot — проверка видео креативов через Telegram.

Кидаешь ссылку на Google Drive папку → бот скачивает видео →
проверяет через ffprobe → присылает отчет.
"""
import logging
from app.config import TELEGRAM_BOT_TOKEN
from app.bot import create_bot

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def main():
    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN не задан в .env")
        return

    log.info("Запускаем File QA Bot...")
    bot = create_bot()
    bot.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
