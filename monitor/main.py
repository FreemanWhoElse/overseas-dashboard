#!/usr/bin/env python3
"""
北京企业出海活动监控看板 — 主监控脚本

工作流程:
  1. 从看板 HTML 或 JSON 加载现有活动数据
  2. 联网抓取 9 个监控来源，发现新活动
  3. 合并新活动，更新过期活动状态
  4. 更新看板 HTML 内嵌数据
  5. 导出未举办活动为 Excel

用法:
  python3 main.py              # 完整流程
  python3 main.py --export-only  # 仅导出 Excel (不联网抓取)
  python3 main.py --test       # 测试模式 (不联网，仅验证解析/导出)
"""
import sys
import os
import logging
from datetime import datetime

# 把当前目录加入 path 以便导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DASHBOARD_HTML, DATA_JSON, EXPORTS_DIR, LOGS_DIR, SOURCES,
    GIT_AUTO_PUSH, GIT_COMMIT_MSG,
)
from updater import (
    extract_events_from_html, load_json, save_json,
    merge_events, update_html, update_status_by_date,
)
from exporter import export_unheld_events
from scraper import scrape_all_sources

import subprocess


def git_push():
    """提交并推送更新到 GitHub。"""
    logger = logging.getLogger()
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = GIT_COMMIT_MSG.format(date=now)

    try:
        # git add
        subprocess.run(
            ["git", "add", "index.html", "data/events.json"],
            cwd=project_dir, check=True, capture_output=True, text=True,
        )
        # 检查是否有变更
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=project_dir, capture_output=True,
        )
        if result.returncode == 0:
            logger.info("无变更，跳过 git 提交")
            return False

        # git commit
        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=project_dir, check=True, capture_output=True, text=True,
        )
        logger.info("git 提交: %s", msg)

        # git push
        subprocess.run(
            ["git", "push"],
            cwd=project_dir, check=True, capture_output=True, text=True,
        )
        logger.info("git 推送成功 — GitHub Pages 将自动更新")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("git 操作失败: %s", e.stderr or e.stdout or str(e))
        logger.error("可手动执行: cd %s && git add . && git commit -m '%s' && git push",
                     project_dir, msg)
        return False
    except FileNotFoundError:
        logger.error("git 命令未找到，请确认已安装 git")
        return False


def setup_logging():
    """配置日志，同时输出到文件和控制台。"""
    os.makedirs(LOGS_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOGS_DIR, f"monitor_{today}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger()


def load_events():
    """加载现有活动数据。优先从 JSON 加载，其次从 HTML 解析。"""
    events = load_json()
    if events is None:
        logger = logging.getLogger()
        logger.info("JSON 数据不存在，从 HTML 解析...")
        events = extract_events_from_html()
    return events


def run_full():
    """完整流程: 抓取 -> 合并 -> 更新 -> 导出"""
    logger = logging.getLogger()
    logger.info("=" * 60)
    logger.info("北京企业出海活动监控看板 — 开始运行")
    logger.info("时间: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # 1. 加载现有数据
    events = load_events()
    logger.info("现有活动: %d 个", len(events))

    # 2. 更新过期活动状态
    update_status_by_date(events)

    # 3. 联网抓取
    logger.info("开始联网抓取 %d 个来源...", len(SOURCES))
    new_events = scrape_all_sources()
    logger.info("抓取完成，发现 %d 个潜在新活动", len(new_events))

    # 4. 合并
    events, added = merge_events(events, new_events)

    # 5. 保存
    save_json(events)
    update_html(events)

    # 6. 导出 Excel
    filepath = export_unheld_events(events)

    # 7. 推送到 GitHub
    if GIT_AUTO_PUSH and "--no-push" not in sys.argv:
        git_push()

    logger.info("=" * 60)
    logger.info("运行完成")
    logger.info("  现有活动: %d 个", len(events))
    logger.info("  新增活动: %d 个", len(added))
    logger.info("  Excel: %s", filepath)
    logger.info("=" * 60)
    return filepath


def run_export_only():
    """仅导出 Excel (不联网抓取)"""
    logger = logging.getLogger()
    logger.info("仅导出模式 — 不联网抓取")

    events = load_events()
    update_status_by_date(events)
    save_json(events)
    update_html(events)

    filepath = export_unheld_events(events)
    logger.info("Excel 导出: %s", filepath)

    if GIT_AUTO_PUSH and "--no-push" not in sys.argv:
        git_push()

    return filepath


def run_test():
    """测试模式: 验证解析和导出功能"""
    logger = logging.getLogger()
    logger.info("测试模式 — 验证解析和导出功能")

    # 测试 HTML 解析
    events = extract_events_from_html()
    logger.info("HTML 解析结果: %d 个活动", len(events))

    if events:
        # 打印前3个
        for e in events[:3]:
            logger.info("  - [%d] %s (%s-%s-%s) %s",
                        e.get("id"), e.get("title", "")[:30],
                        e.get("year"), e.get("month"), e.get("day"),
                        e.get("statusLabel"))

        # 测试状态更新
        changed = update_status_by_date(events)
        logger.info("状态更新: %d 个活动状态变更", changed)

        # 测试 Excel 导出
        filepath = export_unheld_events(events)
        logger.info("Excel 导出成功: %s", filepath)
        return filepath
    else:
        logger.error("HTML 解析失败，未获取到活动数据")
        return None


if __name__ == "__main__":
    setup_logging()

    if "--test" in sys.argv:
        run_test()
    elif "--export-only" in sys.argv:
        run_export_only()
    else:
        run_full()
用法:
  python3 main.py              # 完整流程 (抓取+更新+导出+推送GitHub)
  python3 main.py --export-only  # 仅导出 Excel (不联网抓取)
  python3 main.py --test       # 测试模式 (不联网，不推送)
  python3 main.py --no-push    # 完整流程但不推送到 GitHub
"""
import sys
import os
import logging
from datetime import datetime

# 把当前目录加入 path 以便导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DASHBOARD_HTML, DATA_JSON, EXPORTS_DIR, LOGS_DIR, SOURCES,
    GIT_AUTO_PUSH, GIT_COMMIT_MSG,
)
from updater import (
    extract_events_from_html, load_json, save_json,
    merge_events, update_html, update_status_by_date,
)
from exporter import export_unheld_events
from scraper import scrape_all_sources

import subprocess


def git_push():
    """提交并推送更新到 GitHub。"""
    logger = logging.getLogger()
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = GIT_COMMIT_MSG.format(date=now)

    try:
        # git add
        subprocess.run(
            ["git", "add", "index.html", "data/events.json"],
            cwd=project_dir, check=True, capture_output=True, text=True,
        )
        # 检查是否有变更
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=project_dir, capture_output=True,
        )
        if result.returncode == 0:
            logger.info("无变更，跳过 git 提交")
            return False

        # git commit
        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=project_dir, check=True, capture_output=True, text=True,
        )
        logger.info("git 提交: %s", msg)

        # git push
        subprocess.run(
            ["git", "push"],
            cwd=project_dir, check=True, capture_output=True, text=True,
        )
        logger.info("git 推送成功 — GitHub Pages 将自动更新")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("git 操作失败: %s", e.stderr or e.stdout or str(e))
        logger.error("可手动执行: cd %s && git add . && git commit -m '%s' && git push",
                     project_dir, msg)
        return False
    except FileNotFoundError:
        logger.error("git 命令未找到，请确认已安装 git")
        return False


def setup_logging():
    """配置日志，同时输出到文件和控制台。"""
    os.makedirs(LOGS_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOGS_DIR, f"monitor_{today}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger()


def load_events():
    """加载现有活动数据。优先从 JSON 加载，其次从 HTML 解析。"""
    events = load_json()
    if events is None:
        logger = logging.getLogger()
        logger.info("JSON 数据不存在，从 HTML 解析...")
        events = extract_events_from_html()
    return events


def run_full():
    """完整流程: 抓取 -> 合并 -> 更新 -> 导出 -> 推送"""
    logger = logging.getLogger()
    logger.info("=" * 60)
    logger.info("北京企业出海活动监控看板 — 开始运行")
    logger.info("时间: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # 1. 加载现有数据
    events = load_events()
    logger.info("现有活动: %d 个", len(events))

    # 2. 更新过期活动状态
    update_status_by_date(events)

    # 3. 联网抓取
    logger.info("开始联网抓取 %d 个来源...", len(SOURCES))
    new_events = scrape_all_sources()
    logger.info("抓取完成，发现 %d 个潜在新活动", len(new_events))

    # 4. 合并
    events, added = merge_events(events, new_events)

    # 5. 保存
    save_json(events)
    update_html(events)

    # 6. 导出 Excel
    filepath = export_unheld_events(events)

    # 7. 推送到 GitHub
    if GIT_AUTO_PUSH and "--no-push" not in sys.argv:
        git_push()

    logger.info("=" * 60)
    logger.info("运行完成")
    logger.info("  现有活动: %d 个", len(events))
    logger.info("  新增活动: %d 个", len(added))
    logger.info("  Excel: %s", filepath)
    logger.info("=" * 60)
    return filepath


def run_export_only():
    """仅导出 Excel (不联网抓取)"""
    logger = logging.getLogger()
    logger.info("仅导出模式 — 不联网抓取")

    events = load_events()
    update_status_by_date(events)
    save_json(events)
    update_html(events)

    filepath = export_unheld_events(events)
    logger.info("Excel 导出: %s", filepath)

    if GIT_AUTO_PUSH and "--no-push" not in sys.argv:
        git_push()

    return filepath


def run_test():
    """测试模式: 验证解析和导出功能"""
    logger = logging.getLogger()
    logger.info("测试模式 — 验证解析和导出功能")

    # 测试 HTML 解析
    events = extract_events_from_html()
    logger.info("HTML 解析结果: %d 个活动", len(events))

    if events:
        # 打印前3个
        for e in events[:3]:
            logger.info("  - [%d] %s (%s-%s-%s) %s",
                        e.get("id"), e.get("title", "")[:30],
                        e.get("year"), e.get("month"), e.get("day"),
                        e.get("statusLabel"))

        # 测试状态更新
        changed = update_status_by_date(events)
        logger.info("状态更新: %d 个活动状态变更", changed)

        # 测试 Excel 导出
        filepath = export_unheld_events(events)
        logger.info("Excel 导出成功: %s", filepath)
        return filepath
    else:
        logger.error("HTML 解析失败，未获取到活动数据")
        return None


if __name__ == "__main__":
    setup_logging()

    if "--test" in sys.argv:
        run_test()
    elif "--export-only" in sys.argv:
        run_export_only()
    else:
        run_full()
