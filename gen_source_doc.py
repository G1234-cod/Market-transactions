"""
软著源代码文档生成器 —— 2026新规版
- 去除所有空行
- 每页恰好50行代码
- 行号全局连续：第1页 1-50，第2页 51-100，...
- 前30页(开头) + 后30页(结尾)，末页为完整模块
"""
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"d:\Market-transactions")
SOFTWARE_NAME = "智能二手商品发布助手"
VERSION = "V1.0"
OUTPUT_PATH = BASE_DIR / "软著申请_源代码文档.txt"

PER_PAGE = 50
FIRST_PAGES = 30
LAST_PAGES = 30

CORE_FILES_BACKEND = [
    "backend/main.py", "backend/run-backend.py",
    "backend/app/__init__.py", "backend/app/config.py", "backend/app/dependencies.py",
    "backend/app/auth/__init__.py", "backend/app/auth/jwt_handler.py",
    "backend/app/db/__init__.py", "backend/app/db/connection.py", "backend/app/db/crud.py",
    "backend/app/models/__init__.py", "backend/app/models/schemas.py",
    "backend/app/routers/__init__.py", "backend/app/routers/auth.py",
    "backend/app/routers/detect.py", "backend/app/routers/extract.py",
    "backend/app/routers/generate.py", "backend/app/routers/history.py",
    "backend/app/routers/market.py", "backend/app/routers/price.py",
    "backend/app/routers/price_history.py", "backend/app/routers/process.py",
    "backend/app/routers/recognition.py", "backend/app/routers/search.py",
    "backend/app/routers/admin.py", "backend/app/routers/notifications.py",
    "backend/app/services/__init__.py", "backend/app/services/price_service.py",
    "backend/app/services/crawler_service.py", "backend/app/services/history_estimator.py",
    "backend/app/services/vision_service.py", "backend/app/services/image_processor.py",
    "backend/app/services/damage_detector.py", "backend/app/services/audit_service.py",
    "backend/app/services/text_service.py",
    "backend/app/ml/__init__.py", "backend/app/ml/yolo_detector.py",
    "backend/app/ml/clip_extractor.py", "backend/app/ml/defect_detector_yolo.py",
    "backend/app/ml/qdrant_client.py", "backend/app/ml/data_collector.py",
    "backend/app/ml/models/__init__.py",
    "backend/app/llm/__init__.py", "backend/app/llm/base.py",
    "backend/app/llm/deepseek_client.py", "backend/app/llm/deepseek_price_client.py",
    "backend/app/llm/qwen_vl_client.py",
    "backend/app/middleware/__init__.py", "backend/app/middleware/rate_limit.py",
    "backend/app/utils/__init__.py", "backend/app/utils/preprocess.py",
    "backend/app/utils/file_validator.py", "backend/app/utils/image_utils.py",
    "backend/app/utils/font_utils.py", "backend/app/utils/json_utils.py",
    "backend/app/utils/background_tasks.py",
    "backend/app/constants/__init__.py", "backend/app/constants/categories.py",
    "backend/scripts/index_items.py",
]

CORE_FILES_FRONTEND = [
    "frontend/src/main.js", "frontend/src/App.vue",
    "frontend/src/api/index.js", "frontend/src/store/user.js",
    "frontend/src/components/ConfirmCard.vue", "frontend/src/components/HistoryCard.vue",
    "frontend/src/components/ImageUploader.vue", "frontend/src/components/TypewriterText.vue",
    "frontend/src/views/HomePage.vue", "frontend/src/views/LoginPage.vue",
    "frontend/src/views/RegisterPage.vue", "frontend/src/views/MarketPage.vue",
    "frontend/src/views/SearchPage.vue", "frontend/src/views/HistoryPage.vue",
    "frontend/src/views/NotificationPage.vue", "frontend/src/views/PriceHistoryPage.vue",
    "frontend/src/views/AdminPanel.vue",
]


def is_blank(line: str) -> bool:
    """纯空行（只有空白字符或换行）"""
    return len(line.strip()) == 0


def is_separator(line: str) -> bool:
    """文件分隔符"""
    return bool(re.match(r'^[=#\-/*]{10,}$', line.strip()))


def read_file_lines(filepath: Path) -> list:
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except Exception:
        return []


def collect_and_filter():
    """
    收集所有源代码，去除空行和分隔符，记录文件边界（基于过滤后的行号）
    只保留有效代码行（非空行）
    """
    filtered_lines = []       # 过滤后的行
    file_ranges = []          # 每个文件在 filtered_lines 中的 [start, end)（0-based）

    for rel_path in CORE_FILES_BACKEND + CORE_FILES_FRONTEND:
        full_path = BASE_DIR / rel_path
        if not full_path.exists():
            continue
        lines = read_file_lines(full_path)
        if not lines:
            continue

        start_idx = len(filtered_lines)

        for line in lines:
            stripped = line.rstrip('\n\r')
            if is_blank(stripped) or is_separator(stripped):
                continue
            filtered_lines.append(stripped)

        end_idx = len(filtered_lines)
        if end_idx > start_idx:
            file_ranges.append({
                "file": rel_path,
                "start": start_idx,  # 0-based inclusive
                "end": end_idx,      # 0-based exclusive
            })

    return filtered_lines, file_ranges


def build_60_pages(flat_lines: list, file_ranges: list):
    """
    前30页：从开头正向，每页50行
    后30页：从最后一个文件边界反向，每页50行，末页=完整模块
    行号全局连续：1-3000
    """
    total = len(flat_lines)
    pages = []

    # ---- 前30页 ----
    cursor = 0
    for pg in range(FIRST_PAGES):
        end = cursor + PER_PAGE
        if end > total:
            end = total
        pages.append({
            "start": cursor,
            "end": end,
            "line_count": end - cursor,
        })
        cursor = end

    # ---- 后30页：从最后一个文件边界反向，每页严格50行 ----
    last_file_end = file_ranges[-1]["end"]  # 最后文件的结束位置
    back_pages = []
    cur_end = last_file_end

    for pg in range(LAST_PAGES):
        cur_start = cur_end - PER_PAGE
        if cur_start < 0:
            cur_start = 0

        back_pages.append({
            "start": cur_start,
            "end": cur_end,
            "line_count": cur_end - cur_start,
        })
        cur_end = cur_start

    back_pages.reverse()  # 恢复正向

    # 验证最后一页确实是50行且结束于文件末尾
    last_bp = back_pages[-1]
    assert last_bp["end"] == last_file_end, f"Last page end {last_bp['end']} != last file end {last_file_end}"

    # ---- 组装全部60页 ----
    all_pages = []
    line_no = 1

    for fp in pages:
        all_pages.append({
            "display_num": len(all_pages) + 1,
            "lines": flat_lines[fp["start"]:fp["end"]],
            "start_line_no": line_no,
            "end_line_no": line_no + fp["line_count"] - 1,
            "line_count": fp["line_count"],
        })
        line_no += fp["line_count"]

    for bp in back_pages:
        all_pages.append({
            "display_num": len(all_pages) + 1,
            "lines": flat_lines[bp["start"]:bp["end"]],
            "start_line_no": line_no,
            "end_line_no": line_no + bp["line_count"] - 1,
            "line_count": bp["line_count"],
        })
        line_no += bp["line_count"]

    return all_pages


def generate_txt(pages: list):
    now = datetime.now().strftime("%Y年%m月%d日")
    total_lines = sum(p["line_count"] for p in pages)

    out = []
    sep = "=" * 72

    out.append(sep)
    out.append(f"     {SOFTWARE_NAME} {VERSION}")
    out.append("     软件著作权登记 —— 源代码文档")
    out.append("")
    out.append(f"     开发完成日期：2025年__月__日")
    out.append(f"     开发方式：合作开发    开发人数：2人")
    out.append(f"     编程语言：Python (FastAPI) + JavaScript (Vue 3)")
    out.append(f"     提交：前{FIRST_PAGES}页(开头) + 后{LAST_PAGES}页(结尾) = {FIRST_PAGES+LAST_PAGES}页")
    out.append(f"     每页：{PER_PAGE}行    总行数：{total_lines}行")
    out.append(f"     生成日期：{now}")
    out.append(sep)
    out.append("")

    for pg in pages:
        num = pg["display_num"]
        lines = pg["lines"]
        start_ln = pg["start_line_no"]

        out.append(chr(12))  # 换页符
        out.append(f"{SOFTWARE_NAME} {VERSION}                                        第 {num} / {len(pages)} 页")
        out.append("-" * 72)

        for line in lines:
            out.append(line)

        out.append("-" * 72)
        out.append(f"第 {num} / {len(pages)} 页")
        out.append("")

    return "\n".join(out)


def main():
    print("=" * 60)
    print(f"  Source Doc Generator - {SOFTWARE_NAME} {VERSION}")
    print("=" * 60)

    # 1. collect & filter
    print("\n[1/3] Collecting & filtering (remove blanks)...")
    flat_lines, file_ranges = collect_and_filter()
    print(f"  Filtered lines: {len(flat_lines)} (no blanks/separators)")
    print(f"  Files: {len(file_ranges)}")
    print(f"  Last file: {file_ranges[-1]['file']}")

    # 2. build pages
    print(f"\n[2/3] Building {FIRST_PAGES}+{LAST_PAGES}={FIRST_PAGES+LAST_PAGES} pages...")
    pages = build_60_pages(flat_lines, file_ranges)
    print(f"  Pages: {len(pages)}")

    for pg in pages:
        print(f"    Page {pg['display_num']:>3}: lines {pg['start_line_no']:>5}-{pg['end_line_no']:>5}  ({pg['line_count']} lines)")

    # verify last page ends at complete module
    last_page_start = pages[-1]["lines"][0] if pages[-1]["lines"] else ""
    print(f"  Last page first line: {last_page_start[:60]}...")

    # 3. generate
    print(f"\n[3/3] Generating -> {OUTPUT_PATH}")
    txt = generate_txt(pages)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(txt)

    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"  Done! {size_kb:.1f} KB")
    print(f"  -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
