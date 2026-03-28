# Clappix File QA Bot

Telegram bot that checks video creatives for quality issues. Send a Google Drive folder link — get a QA report in seconds. No downloads, works via API metadata.

## How It Works

```
Google Drive Folder Link
         │
         ▼
┌────────────────────┐
│  Google Drive API   │  ← Recursively scan all subfolders
│  (no downloads!)    │  ← Get metadata: resolution, duration, size
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  QA Rules Engine    │  ← Check naming, resolution, duration, format
└────────┬───────────┘
         │
         ▼
   Report in Telegram
   ✅ 61 Passed
   ❌ 3 Failed (with links)
```

## QA Checks

| Check | What it catches |
|-------|----------------|
| Resolution mismatch | Filename says 1920x1080 but actual is 1080x1920 |
| Duration mismatch | Filename says 30s but video is 25s |
| Wrong folder | File v797 is inside folder v871 |
| Naming format | Missing language code, duration, or wrong template |
| File size | Over 40 MB |
| Duration limit | Over 30 seconds |
| Format | Not .mp4 |

## Why Not Download?

Traditional QA tools download every file to analyze it. This bot uses **Google Drive API metadata** — resolution, duration, and size are available without downloading. This means:

- **100 files** → 5 seconds (not 30 minutes)
- **10,000 files** → still seconds
- **Zero bandwidth** used

## Quick Start

### 1. Setup

```bash
git clone https://github.com/YourUser/clappix-file-qa.git
cd clappix-file-qa
cp .env.example .env
```

### 2. Configure

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your-token-from-botfather
GOOGLE_CREDENTIALS_PATH=./credentials.json
```

### 3. Google Service Account

1. Create a service account in [Google Cloud Console](https://console.cloud.google.com)
2. Download JSON key → save as `credentials.json`
3. Share your Drive folder with the service account email (Viewer is enough)

### 4. Run

```bash
pip install -r requirements.txt
python main.py
```

Or with Docker:
```bash
docker compose up --build
```

### 5. Use

Send a Google Drive folder link to the bot → get a report.

## Naming Convention

Expected format: `ad_WIDTHxHEIGHT_vNNN_lang_type_XXs.mp4`

Example: `ad_1080x1920_v744_en_pn_29s.mp4`

| Part | Meaning |
|------|---------|
| `ad_` | Prefix |
| `1080x1920` | Resolution |
| `v744` | Version / project number |
| `en` | Language |
| `pn` | Type (pn, rp-rt, nl, etc.) |
| `29s` | Duration in seconds |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Bot | python-telegram-bot |
| Cloud | Google Drive API (metadata only) |
| Deployment | Docker |

## License

MIT
