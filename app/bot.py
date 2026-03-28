"""
Telegram бот для QA проверки видео креативов.

Флоу:
1. Кидаешь ссылку на Google Drive папку
2. Бот скачивет все видео
3. Проверяет через ffprobe
4. Присылает отчёт
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from app.config import TELEGRAM_BOT_TOKEN
from app.drive import extract_folder_id, extract_file_id, list_video_files, get_single_file, is_file_link
from app.checker import check_files, check_file, format_report

log = logging.getLogger(__name__)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I'm the File QA Bot.\n\n"
        "Send me a Google Drive folder link and I'll check all video files inside.\n\n"
        "I'll verify:\n"
        "• Resolution (min 1920x1080)\n"
        "• FPS (24-60)\n"
        "• Duration (max 120s)\n"
        "• Format (mp4, mov, webm)\n"
        "• File size (max 500MB)\n\n"
        "Just paste a link like:\n"
        "https://drive.google.com/drive/folders/1ABC...xyz"
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 How to use:\n\n"
        "1. Share your Google Drive folder with the service account email\n"
        "2. Send me the folder link\n"
        "3. Wait for the report\n\n"
        "Commands:\n"
        "/start — Welcome\n"
        "/help — This message\n"
        "/rules — Current QA rules"
    )


async def cmd_rules(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from app.config import (
        MIN_WIDTH, MIN_HEIGHT, MIN_FPS, MAX_FPS,
        MAX_DURATION_SEC, ALLOWED_FORMATS, MAX_FILE_SIZE_MB,
    )
    await update.message.reply_text(
        f"📏 Current QA Rules:\n\n"
        f"Resolution: min {MIN_WIDTH}x{MIN_HEIGHT}\n"
        f"FPS: {MIN_FPS}—{MAX_FPS}\n"
        f"Duration: max {MAX_DURATION_SEC}s\n"
        f"Formats: {', '.join(ALLOWED_FORMATS)}\n"
        f"Max size: {MAX_FILE_SIZE_MB} MB"
    )


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Основной хендлер — ловим ссылку на Google Drive.
    Если это не ссылка — просим прислать ссылку.
    """
    text = update.message.text.strip()

    # Проверяем тип ссылки — файл или папка
    if is_file_link(text):
        # Ссылка на один файл
        file_id = extract_file_id(text)
        if not file_id:
            await update.message.reply_text("🤔 Can't parse file ID from this link.")
            return

        await update.message.reply_text("🔍 Checking file...")

        try:
            f = get_single_file(file_id)
            if not f:
                await update.message.reply_text("❌ Can't access this file. Make sure it's shared.")
                return

            result = check_file(f)
            report = format_report([result])

            await update.message.reply_text(report)
            return

        except Exception as e:
            log.error("Error checking file: %s", e, exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)}")
            return

    folder_id = extract_folder_id(text)
    if not folder_id:
        await update.message.reply_text(
            "🤔 That doesn't look like a Google Drive link.\n"
            "Send me a folder or file link."
        )
        return

    # Проверка папки
    await update.message.reply_text(f"📂 Found folder. Scanning for video files...")

    try:
        # Шаг 1: получаем список файлов
        files = list_video_files(folder_id)
        if not files:
            await update.message.reply_text("📭 No video files found in this folder.")
            return

        await update.message.reply_text(
            f"🎬 Found {len(files)} video files. Checking via API..."
        )

        # Шаг 2: проверяем по метаданным (без скачивания)
        results = check_files(files)

        # Шаг 3: формируем и отправляем отчёт
        report = format_report(results)

        # Телеграм лимит — 4096 символов, режем если надо
        if len(report) > 4000:
            # Отправляем частями
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(report)

    except Exception as e:
        log.error("Error processing folder: %s", e, exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")


def create_bot() -> Application:
    """Создаём и настраиваем бота."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
