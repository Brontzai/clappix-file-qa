"""
Скрипт для загрузки видео на Google Drive.
Создаёт структуру папок: v771/ → video + assets/ + collects/
"""
import os
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

CREDS_PATH = "./credentials.json"
PARENT_FOLDER_ID = "1xjHhwu8e3w3Lp6Ju4QKNBZ8MvhStGg8O"  # папка на Drive
SOURCE_DIR = "/Volumes/Secret Data/mycreo/coem"


def get_service():
    creds = Credentials.from_service_account_file(
        CREDS_PATH,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def create_folder(service, name, parent_id):
    """Создаём папку на Drive."""
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_file(service, filepath, parent_id, new_name=None):
    """Заливаем файл на Drive."""
    name = new_name or os.path.basename(filepath)
    meta = {"name": name, "parents": [parent_id]}
    media = MediaFileUpload(filepath, resumable=True)
    f = service.files().create(body=meta, media_body=media, fields="id").execute()
    return f["id"]


def extract_version(filename):
    """Вытаскиваем номер версии из имени: ce_1080x1080_v771_it_rp-rt_30s.mp4 → v771"""
    match = re.search(r"(v\d+)", filename)
    return match.group(1) if match else None


def rename_file(filename):
    """ce_1080x1080_v771_it_rp-rt_30s.mp4 → ad_1080x1080_v771_it_rp-rt_30s.mp4"""
    return filename.replace("ce_", "ad_", 1)


def main():
    service = get_service()
    files = sorted(os.listdir(SOURCE_DIR))
    files = [f for f in files if f.endswith(".mp4")]

    print(f"Found {len(files)} videos")

    for i, filename in enumerate(files):
        version = extract_version(filename)
        if not version:
            print(f"  SKIP (no version): {filename}")
            continue

        new_name = rename_file(filename)
        filepath = os.path.join(SOURCE_DIR, filename)

        print(f"[{i+1}/{len(files)}] {version} — {new_name}")

        # Создаём папку vXXX
        folder_id = create_folder(service, version, PARENT_FOLDER_ID)

        # Создаём подпапки assets и collects
        create_folder(service, "assets", folder_id)
        create_folder(service, "collects", folder_id)

        # Заливаем видео
        upload_file(service, filepath, folder_id, new_name)
        print(f"  ✓ uploaded")

    print(f"\nDone! {len(files)} videos uploaded.")


if __name__ == "__main__":
    main()
