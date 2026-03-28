"""
Создаём структуру папок на Google Drive для каждого видео.
Ты потом просто перетащишь файлы в нужные папки вручную.
"""
import os
import re
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

CREDS_PATH = "./credentials.json"
PARENT_FOLDER_ID = "1xjHhwu8e3w3Lp6Ju4QKNBZ8MvhStGg8O"
SOURCE_DIR = "/Volumes/Secret Data/mycreo/coem"


def get_service():
    creds = Credentials.from_service_account_file(
        CREDS_PATH,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def create_folder(service, name, parent_id):
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def main():
    service = get_service()
    files = sorted([f for f in os.listdir(SOURCE_DIR) if f.endswith(".mp4")])

    # Вытаскиваем уникальные версии
    versions = {}
    for f in files:
        match = re.search(r"(v\d+)", f)
        if match:
            v = match.group(1)
            if v not in versions:
                versions[v] = []
            versions[v].append(f)

    print(f"Found {len(files)} files, {len(versions)} unique versions\n")

    for i, (version, vfiles) in enumerate(sorted(versions.items(), key=lambda x: int(x[0][1:]))):
        print(f"[{i+1}/{len(versions)}] Creating {version}/")

        # Создаём папку vXXX
        folder_id = create_folder(service, version, PARENT_FOLDER_ID)

        # Создаём подпапки
        create_folder(service, "assets", folder_id)
        create_folder(service, "collects", folder_id)

        # Показываем какие файлы туда положить
        for f in vfiles:
            new_name = f.replace("ce_", "ad_", 1)
            print(f"  → {new_name}")

    print(f"\nDone! Created {len(versions)} folders. Now drag videos into them.")


if __name__ == "__main__":
    main()
