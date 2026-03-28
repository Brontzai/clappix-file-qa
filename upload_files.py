"""Заливаем видео в уже созданные папки на Drive."""
import os
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

CREDS_PATH = "./credentials.json"
PARENT_FOLDER_ID = "1xjHhwu8e3w3Lp6Ju4QKNBZ8MvhStGg8O"
SOURCE_DIR = "/Volumes/Secret Data/mycreo/coem"


def get_service():
    creds = Credentials.from_service_account_file(
        CREDS_PATH, scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def main():
    service = get_service()

    # Получаем список папок на Drive
    results = service.files().list(
        q=f"'{PARENT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        pageSize=200, fields="files(id, name)",
    ).execute()
    folders = {f["name"]: f["id"] for f in results.get("files", [])}
    print(f"Found {len(folders)} folders on Drive")

    # Получаем файлы
    files = sorted([f for f in os.listdir(SOURCE_DIR) if f.endswith(".mp4") and not f.startswith("._")])
    print(f"Found {len(files)} videos to upload\n")

    for i, filename in enumerate(files):
        match = re.search(r"(v\d+)", filename)
        if not match:
            continue
        version = match.group(1)
        if version not in folders:
            print(f"  SKIP {filename} — no folder {version}")
            continue

        new_name = filename.replace("ce_", "ad_", 1)
        filepath = os.path.join(SOURCE_DIR, filename)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        print(f"[{i+1}/{len(files)}] Uploading {new_name} ({size_mb:.1f} MB)...")

        meta = {"name": new_name, "parents": [folders[version]]}
        media = MediaFileUpload(filepath, resumable=True, chunksize=10*1024*1024)
        request = service.files().create(body=meta, media_body=media, fields="id")

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  {int(status.progress() * 100)}%")

        print(f"  ✓ done")

    print("\nAll files uploaded!")


if __name__ == "__main__":
    main()
