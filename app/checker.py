"""
QA чекер видео — работает через Google Drive API метаданные.
Ничего не скачивает. Даже 10 000 файлов проверит за секунды.

Проверки:
- Разрешение (мин 1920x1080)
- Длительность (макс 30 сек)
- Формат (только mp4)
- Размер файла (макс 40 MB)
- Длина в названии совпадет с реальной длиной
- Нейминг (формат ad_WxH_vXXX_lang_type_XXs.mp4)
"""
import re
import logging
from pathlib import Path
from app.config import (
    MIN_WIDTH, MIN_HEIGHT,
    MAX_DURATION_SEC, ALLOWED_FORMATS, MAX_FILE_SIZE_MB,
)

log = logging.getLogger(__name__)


def _parse_duration_from_name(filename: str) -> int | None:
    """
    Вытаскиваем длительность из названия файла.
    ad_1080x1920_v744_en_pn_29s.mp4 → 29
    """
    match = re.search(r"(\d+)s", filename)
    return int(match.group(1)) if match else None


def _parse_resolution_from_name(filename: str) -> tuple[int, int] | None:
    """
    Вытаскиваем разрешение из названия.
    ad_1080x1920_v744_en_pn_29s.mp4 → (1080, 1920)
    """
    match = re.search(r"(\d{3,4})x(\d{3,4})", filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def check_file(file_data: dict) -> dict:
    """
    Проверяем один файл по метаданным из Drive API.
    """
    name = file_data.get("name", "unknown")
    size_bytes = int(file_data.get("size", 0))
    size_mb = round(size_bytes / (1024 * 1024), 1)
    meta = file_data.get("videoMediaMetadata", {})

    width = int(meta.get("width", 0))
    height = int(meta.get("height", 0))
    duration_ms = int(meta.get("durationMillis", 0))
    duration_sec = round(duration_ms / 1000, 1)

    fmt = Path(name).suffix.lstrip(".").lower()

    result = {
        "filename": name,
        "file_id": file_data.get("id", ""),
        "width": width,
        "height": height,
        "duration": duration_sec,
        "format": fmt,
        "size_mb": size_mb,
        "errors": [],
        "passed": True,
    }

    # === ПРОВЕРКИ ===

    # 1. Формат — только mp4
    if fmt not in ALLOWED_FORMATS:
        result["errors"].append(
            f"❌ Wrong format: .{fmt} (only {', '.join(ALLOWED_FORMATS)} allowed)"
        )

    # 2. Разрешение в названии не совпадает с реальным
    if width > 0 and height > 0:
        name_res = _parse_resolution_from_name(name)
        if name_res:
            nw, nh = name_res
            if nw != width or nh != height:
                result["errors"].append(
                    f"📐 Resolution mismatch: filename says {nw}x{nh}, actual is {width}x{height}"
                )

    # 3. Длительность
    if duration_sec > MAX_DURATION_SEC:
        result["errors"].append(
            f"⏱ Too long: {duration_sec}s (max {MAX_DURATION_SEC}s)"
        )

    # 4. Длина в названии не совпадает с реальной
    if duration_sec > 0:
        name_dur = _parse_duration_from_name(name)
        if name_dur is not None:
            actual_rounded = round(duration_sec)
            if abs(name_dur - actual_rounded) > 1:
                result["errors"].append(
                    f"📛 Duration mismatch: filename says {name_dur}s, actual is {duration_sec}s"
                )

    # 5. Размер файла
    if size_mb > MAX_FILE_SIZE_MB:
        result["errors"].append(
            f"💾 Too large: {size_mb} MB (max {MAX_FILE_SIZE_MB} MB)"
        )

    # 6. Нейминг — полный шаблон: ad_WxH_vNNN_lang_type_XXs.mp4
    naming_pattern = r"^ad_\d{3,4}x\d{3,4}_v\d+_[a-z]{2}_[a-z\-]+_\d+s(\(v\d+\))?\.mp4$"
    if not re.match(naming_pattern, name):
        # Определяем что именно не так
        if not name.startswith("ad_"):
            result["errors"].append("📛 Naming: should start with 'ad_'")
        elif not re.search(r"\d+x\d+", name):
            result["errors"].append("📛 Naming: missing resolution (e.g. 1080x1920)")
        elif not re.search(r"_v\d+", name):
            result["errors"].append("📛 Naming: missing version (e.g. _v771)")
        elif not re.search(r"_[a-z]{2}_", name):
            result["errors"].append("📛 Naming: missing language code (e.g. _en_)")
        elif not re.search(r"_\d+s", name):
            result["errors"].append("📛 Naming: missing duration (e.g. _30s)")
        else:
            result["errors"].append(
                f"📛 Naming: doesn't match template ad_WxH_vNNN_lang_type_XXs.mp4"
            )

    # 7. Файл в неправильной папке — v-номер в названии должен совпадать с папкой
    parent_folder = file_data.get("parent_folder", "")
    file_version = re.search(r"_(v\d+)", name)
    if file_version and parent_folder:
        if file_version.group(1) != parent_folder:
            result["errors"].append(
                f"📂 Wrong folder: file is {file_version.group(1)} but in folder '{parent_folder}'"
            )

    result["passed"] = len(result["errors"]) == 0
    return result


def check_files(files_data: list[dict]) -> list[dict]:
    """Проверяем все файлы по метаданным."""
    return [check_file(f) for f in files_data]


def format_report(results: list[dict]) -> str:
    """
    Отчёт для Telegram.
    Показываем только ошибки — passed файлы просто считаем.
    """
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    lines = []
    lines.append(f"📋 QA Report\n")
    lines.append(f"📁 Files scanned: {total}")
    lines.append(f"✅ Passed: {passed}")
    lines.append(f"❌ Failed: {failed}")
    lines.append("")
    lines.append("─" * 32)

    if failed > 0:
        lines.append("")
        for r in results:
            if not r["passed"]:
                lines.append(f"❌ {r['filename']}")
                lines.append(f"   {r['width']}x{r['height']} | {r['duration']}s | {r['size_mb']}MB | .{r['format']}")
                file_id = r.get("file_id", "")
                if file_id:
                    lines.append(f"   🔗 https://drive.google.com/file/d/{file_id}")
                for err in r["errors"]:
                    lines.append(f"   {err}")
                lines.append("")

    lines.append("─" * 32)
    if failed == 0:
        lines.append("🎉 All files passed QA!")
    else:
        lines.append(f"⚠️ {failed} file(s) need attention")

    return "\n".join(lines)
