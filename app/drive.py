"""
Модуль для работы с Google Drive.
Получаем ссылку на папку → скачиваем все видео файлы из неё.

Поддерживает ссылки вида:
- https://drive.google.com/drive/folders/FOLDER_ID
- https://drive.google.com/drive/u/0/folders/FOLDER_ID
"""
import os
import re
import logging
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
from app.config import GOOGLE_CREDENTIALS_PATH, TEMP_DIR

log = logging.getLogger(__name__)

# Видео форматы которые будем качать
VIDEO_MIMES = [
    "video/mp4", "video/quicktime", "video/webm",
    "video/x-msvideo", "video/x-matroska",
]


def _get_drive_service():
    """Подключаемся к Google Drive через сервисный аккаунт."""
    creds = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    return build("drive", "v3", credentials=creds)


def extract_folder_id(url: str) -> str | None:
    """
    Вытаскиваем ID папки из ссылки Google Drive.
    Пример: https://drive.google.com/drive/folders/1ABC...xyz → 1ABC...xyz
    """
    patterns = [
        r"folders/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    return None


def extract_file_id(url: str) -> str | None:
    """
    Вытаскиваем ID файла из ссылки.
    https://drive.google.com/file/d/1ABC...xyz/view → 1ABC...xyz
    """
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


def get_single_file(file_id: str) -> dict | None:
    """Получаем метаданные одного файла по ID."""
    service = _get_drive_service()
    try:
        f = service.files().get(
            fileId=file_id,
            fields="id,name,size,mimeType,videoMediaMetadata,parents",
            supportsAllDrives=True,
        ).execute()
        # Пробуем получить имя папки-родителя
        parents = f.get("parents", [])
        if parents:
            parent = service.files().get(
                fileId=parents[0], fields="name", supportsAllDrives=True,
            ).execute()
            f["parent_folder"] = parent.get("name", "")
        return f
    except Exception as e:
        log.error("Не удалось получить файл %s: %s", file_id, e)
        return None


def is_file_link(url: str) -> bool:
    """Проверяем что это ссылка на файл а не папку."""
    return "/file/d/" in url or "/d/" in url and "folders" not in url


def list_video_files(folder_id: str) -> list[dict]:
    """
    Получаем список видео файлов рекурсивно — ищем в подпапках тоже.
    Сразу тянем метадату (разрешение, длительность) — ничего не скачиваем.
    Возвращает [{id, name, size, mimeType, videoMediaMetadata}, ...]
    """
    service = _get_drive_service()
    all_videos = []

    def _scan_folder(fid, folder_name=""):
        query = f"'{fid}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            pageSize=500,
            fields="files(id, name, size, mimeType, videoMediaMetadata)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = results.get("files", [])

        for f in files:
            if f.get("mimeType") == "application/vnd.google-apps.folder":
                _scan_folder(f["id"], f["name"])
            elif f.get("mimeType", "") in VIDEO_MIMES:
                f["parent_folder"] = folder_name
                all_videos.append(f)

    _scan_folder(folder_id)
    log.info("Нашли %d видео (рекурсивный поиск)", len(all_videos))

    return all_videos


def download_files(files: list[dict]) -> list[str]:
    """
    Скачиваем файлы во врменную папку.
    Возвращает список путей к скачаным файлам.
    """
    service = _get_drive_service()
    os.makedirs(TEMP_DIR, exist_ok=True)

    downloaded = []
    for f in files:
        filepath = os.path.join(TEMP_DIR, f["name"])

        # Если уже скачан — пропускаем
        if os.path.exists(filepath):
            downloaded.append(filepath)
            continue

        log.info("Скачиваем: %s (%s)", f["name"], _fmt_size(int(f.get("size", 0))))

        request = service.files().get_media(fileId=f["id"])
        with open(filepath, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        downloaded.append(filepath)

    return downloaded


def cleanup():
    """Чистим временую папку после проверки."""
    import shutil
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        log.info("Очистили tmp: %s", TEMP_DIR)


def _fmt_size(size_bytes: int) -> str:
    """Форматируем размер файла."""
    if size_bytes >= 1e9:
        return f"{size_bytes/1e9:.1f} GB"
    if size_bytes >= 1e6:
        return f"{size_bytes/1e6:.1f} MB"
    return f"{size_bytes/1e3:.0f} KB"
