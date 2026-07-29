"""
看板数据更新模块
从 HTML 中解析现有活动数据，合并新活动，写回 HTML 和 JSON。
"""
import os
import re
import json
import logging
from datetime import datetime

from config import DASHBOARD_HTML, DATA_JSON, TOPIC_LABELS, VENUE_MAP

logger = logging.getLogger(__name__)

# 用于匹配 HTML 中的 const events = [...]; 块
_EVENTS_PATTERN = re.compile(
    r"const\s+events\s*=\s*\[(.*?)\];",
    re.DOTALL,
)
# 匹配单个事件对象 { id: 1, month: 7, ... }
_OBJ_PATTERN = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _parse_js_value(val):
    """尝试把 JS 字面量转为 Python 值。"""
    val = val.strip()
    if val.startswith('"') or val.startswith("'"):
        return val[1:-1]
    if val == "true":
        return True
    if val == "false":
        return False
    if val == "null" or val == "undefined":
        return None
    if val.startswith("["):
        # 数组: ["a", "b"]
        inner = val[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in _split_array(inner):
            items.append(_parse_js_value(item))
        return items
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def _split_array(text):
    """简单分割 JS 数组元素，处理引号内的逗号。"""
    items = []
    current = ""
    in_quote = False
    quote_char = ""
    for ch in text:
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
            current += ch
        elif ch == quote_char and in_quote:
            in_quote = False
            quote_char = ""
            current += ch
        elif ch == "," and not in_quote:
            items.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        items.append(current.strip())
    return items


def _parse_event_object(obj_str):
    """解析单个 JS 事件对象字符串为字典。"""
    result = {}
    # 去掉首尾的 { }
    inner = obj_str.strip()
    if inner.startswith("{"):
        inner = inner[1:]
    if inner.endswith("}"):
        inner = inner[:-1]

    # 分割键值对 (处理引号内的逗号)
    pairs = []
    current = ""
    in_quote = False
    quote_char = ""
    depth = 0
    for ch in inner:
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
            current += ch
        elif ch == quote_char and in_quote:
            in_quote = False
            quote_char = ""
            current += ch
        elif ch == "[" and not in_quote:
            depth += 1
            current += ch
        elif ch == "]" and not in_quote:
            depth -= 1
            current += ch
        elif ch == "," and not in_quote and depth == 0:
            pairs.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        pairs.append(current.strip())

    for pair in pairs:
        if ":" not in pair:
            continue
        key, val = pair.split(":", 1)
        key = key.strip()
        result[key] = _parse_js_value(val)

    return result


def extract_events_from_html(html_path=None):
    """从 HTML 文件中解析 events 数组，返回事件列表。"""
    html_path = html_path or DASHBOARD_HTML
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    m = _EVENTS_PATTERN.search(content)
    if not m:
        logger.error("未在 HTML 中找到 events 数组")
        return []

    array_body = m.group(1)
    # 提取每个 {} 对象
    events = []
    for obj_match in _OBJ_PATTERN.finditer(array_body):
        try:
            event = _parse_event_object(obj_match.group(0))
            if event and "title" in event:
                events.append(event)
        except Exception as e:
            logger.warning("解析事件对象失败: %s", e)

    logger.info("从 HTML 解析到 %d 个活动", len(events))
    # 补充已知举办地址 (与 HTML 中的 venueMap 保持一致)
    for e in events:
        eid = e.get("id")
        if eid and eid in VENUE_MAP and not e.get("venue"):
            e["venue"] = VENUE_MAP[eid]
        if not e.get("registration"):
            e["registration"] = "详见活动链接"

    return events


def _generate_event_js(event):
    """将单个事件字典生成为 JS 对象字面量字符串。"""
    # 确保 topics 是数组
    topics = event.get("topics", [])
    if isinstance(topics, list):
        topics_js = "[" + ", ".join(f'"{t}"' for t in topics) + "]"
    else:
        topics_js = '["general"]'

    venue = event.get("venue", "")
    registration = event.get("registration", "详见活动链接")

    # 转义字符串中的特殊字符
    def esc(s):
        if not isinstance(s, str):
            s = str(s)
        return s.replace('"', '\\"').replace("\n", " ").replace("\r", "")

    return (
        "  {\n"
        f'    id: {event.get("id", 0)}, '
        f'month: {event.get("month", 1)}, '
        f'day: {event.get("day", 1)}, '
        f'year: {event.get("year", 2026)},\n'
        f'    title: "{esc(event.get("title", ""))}",\n'
        f'    organizer: "{esc(event.get("organizer", ""))}",\n'
        f'    type: "{event.get("type", "forum")}", '
        f'typeLabel: "{esc(event.get("typeLabel", "论坛"))}",\n'
        f"    topics: {topics_js},\n"
        f'    status: "{event.get("status", "upcoming")}", '
        f'statusLabel: "{esc(event.get("statusLabel", "即将举办"))}",\n'
        f'    priority: "{event.get("priority", "normal")}",\n'
        f'    desc: "{esc(event.get("desc", ""))}",\n'
        f'    url: "{esc(event.get("url", ""))}",\n'
        f'    venue: "{esc(venue)}",\n'
        f'    registration: "{esc(registration)}"\n'
        "  }"
    )


def _generate_events_js(events):
    """生成完整的 events 数组 JS 代码。"""
    parts = [_generate_event_js(e) for e in events]
    return "const events = [\n" + ",\n".join(parts) + "\n];"


def update_html(events, html_path=None):
    """将更新后的活动列表写回 HTML 文件。"""
    html_path = html_path or DASHBOARD_HTML
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_js = _generate_events_js(events)
    new_content = _EVENTS_PATTERN.sub(
        lambda m: new_js,
        content,
    )

    # 更新数据快照日期
    today = datetime.now().strftime("%Y-%m-%d")
    new_content = re.sub(
        r'数据快照: \d{4}-\d{2}-\d{2}',
        f'数据快照: {today}',
        new_content,
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    logger.info("看板 HTML 已更新: %s (%d 个活动)", html_path, len(events))


def save_json(events, json_path=None):
    """保存活动数据到 JSON 文件。"""
    json_path = json_path or DATA_JSON
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    logger.info("数据已保存到 JSON: %s", json_path)


def load_json(json_path=None):
    """从 JSON 文件加载活动数据。"""
    json_path = json_path or DATA_JSON
    if not os.path.exists(json_path):
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        events = json.load(f)
    logger.info("从 JSON 加载 %d 个活动", len(events))
    return events


def merge_events(existing, new_events):
    """合并新发现的活动到现有列表，按标题去重。"""
    existing_titles = set()
    for e in existing:
        title = e.get("title", "").strip()
        if title:
            existing_titles.add(title)

    max_id = max((e.get("id", 0) for e in existing), default=0)
    added = []

    for new_e in new_events:
        title = new_e.get("title", "").strip()
        if not title or title in existing_titles:
            continue
        # 模糊匹配: 标题前10字符相同也算重复
        is_dup = False
        for t in existing_titles:
            if title[:10] == t[:10] and len(title) > 5:
                is_dup = True
                break
        if is_dup:
            continue

        max_id += 1
        new_e["id"] = max_id
        existing.append(new_e)
        existing_titles.add(title)
        added.append(new_e)
        logger.info("新增活动: %s", title)

    logger.info("合并完成: 新增 %d 个活动，总计 %d 个", len(added), len(existing))
    return existing, added


def update_status_by_date(events):
    """根据当前日期更新活动状态 (将过去的 upcoming/confirmed 改为 completed)。"""
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)
    changed = 0

    for e in events:
        if e.get("status") in ("upcoming", "confirmed"):
            y = e.get("year")
            m = e.get("month")
            d = e.get("day")
            if y and m and d:
                try:
                    event_date = datetime(y, m, d)
                    if event_date < today:
                        e["status"] = "completed"
                        e["statusLabel"] = "已举办"
                        changed += 1
                except (ValueError, TypeError):
                    pass

    if changed:
        logger.info("状态更新: %d 个活动从「未举办」变为「已举办」", changed)
    return changed
