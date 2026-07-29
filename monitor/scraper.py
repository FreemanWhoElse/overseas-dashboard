"""
网页抓取模块
从各监控来源的列表页抓取链接，按关键词筛选后提取活动详情。
"""
import re
import time
import urllib.request
import urllib.parse
import logging
from datetime import datetime
from lxml import html as lxml_html

from config import KEYWORDS, SOURCES, HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY

logger = logging.getLogger(__name__)


def fetch_url(url, timeout=REQUEST_TIMEOUT):
    """抓取 URL，返回解码后的 HTML 文本。失败返回 None。"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            # 尝试从响应头获取编码，否则尝试自动检测
            charset = resp.headers.get_content_charset()
            if charset:
                return raw.decode(charset, errors="replace")
            # 常见中文编码尝试
            for enc in ("utf-8", "gbk", "gb2312"):
                try:
                    return raw.decode(enc)
                except (UnicodeDecodeError, ValueError):
                    continue
            return raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("抓取失败 %s: %s", url, e)
        return None


def extract_links(html_text, base_url):
    """从 HTML 中提取所有链接及其文本。返回 [(url, text), ...]"""
    try:
        tree = lxml_html.fromstring(html_text)
    except Exception:
        # lxml 解析失败时用正则兜底
        return _extract_links_regex(html_text, base_url)

    links = []
    for a in tree.xpath("//a[@href]"):
        href = a.get("href", "").strip()
        text = a.text_content().strip() if a.text_content() else ""
        if not href or href.startswith(("javascript:", "#", "mailto:")):
            continue
        full_url = urllib.parse.urljoin(base_url, href)
        if text:
            links.append((full_url, text))
    return links


def _extract_links_regex(html_text, base_url):
    """正则兜底的链接提取"""
    links = []
    pattern = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.DOTALL)
    for m in pattern.finditer(html_text):
        href = m.group(1).strip()
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if not href or href.startswith(("javascript:", "#", "mailto:")):
            continue
        full_url = urllib.parse.urljoin(base_url, href)
        if text:
            links.append((full_url, text))
    return links


def matches_keywords(text, keywords=KEYWORDS):
    """检查文本是否包含任一关键词。返回匹配到的关键词列表。"""
    matched = [kw for kw in keywords if kw in text]
    return matched


def parse_date(text):
    """从文本中解析日期，返回 (year, month, day) 或 None。"""
    # 2026年7月28日 / 2026年07月28日
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    # 2026-07-28 / 2026-7-28
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    # 2026.07.28
    m = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    # 07-28 / 7月28日 (无年份，默认当前年)
    m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if m:
        return datetime.now().year, int(m.group(1)), int(m.group(2))
    return None


def extract_venue(text):
    """从文本中提取举办地址。"""
    patterns = [
        r"地点[：:]\s*(.+?)(?:\n|。|；|，|报名|时间)",
        r"地址[：:]\s*(.+?)(?:\n|。|；|，|报名|时间)",
        r"举办地点[：:]\s*(.+?)(?:\n|。|；|，|报名|时间)",
        r"venue[：:]\s*(.+?)(?:\n|。|；|，)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:200]
    return ""


def extract_registration(text):
    """从文本中提取报名方式。"""
    patterns = [
        r"报名[方式链接口径：:]\s*(.+?)(?:\n|。|；)",
        r"注册[方式链接口径：:]\s*(.+?)(?:\n|。|；)",
        r"参加[方式方式：:]\s*(.+?)(?:\n|。|；)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:200]
    return "详见活动链接"


def extract_detail(url):
    """抓取详情页，提取标题、日期、描述、地址、报名方式。"""
    html_text = fetch_url(url)
    if not html_text:
        return None

    try:
        tree = lxml_html.fromstring(html_text)
    except Exception:
        return None

    # 标题: 尝试 h1, title, og:title
    title = ""
    for selector in ["//h1", "//title", '//meta[@property="og:title"]/@content']:
        nodes = tree.xpath(selector)
        if nodes and nodes[0].text_content().strip():
            title = nodes[0].text_content().strip()
            break
    title = re.sub(r"\s+", " ", title).strip()

    # 页面纯文本
    body_text = tree.text_content()
    body_text = re.sub(r"\s+", " ", body_text)

    # 日期
    date_info = parse_date(body_text[:3000])

    # 描述: 取正文前200字
    desc = body_text[:300].strip()
    if len(desc) > 200:
        # 尝试在句号处截断
        cut = desc.rfind("。", 0, 200)
        if cut > 50:
            desc = desc[:cut + 1]

    # 地址和报名方式
    venue = extract_venue(body_text[:5000])
    registration = extract_registration(body_text[:5000])

    return {
        "title": title,
        "date_info": date_info,
        "desc": desc,
        "venue": venue,
        "registration": registration,
    }


def scrape_source(source):
    """抓取单个来源的所有列表页，返回发现的活动列表。"""
    found_events = []
    source_name = source["name"]

    for page_url in source["pages"]:
        logger.info("抓取来源 [%s] 页面: %s", source_name, page_url)
        html_text = fetch_url(page_url)
        if not html_text:
            continue

        links = extract_links(html_text, page_url)
        logger.info("  提取到 %d 个链接", len(links))

        for link_url, link_text in links:
            matched_kws = matches_keywords(link_text)
            if not matched_kws:
                continue

            logger.info("  命中关键词 %s: %s -> %s",
                        matched_kws, link_text[:50], link_url)

            # 抓取详情页
            detail = extract_detail(link_url)
            if not detail or not detail["title"]:
                # 没有详情页信息，用链接文本作为标题
                detail = {
                    "title": link_text,
                    "date_info": None,
                    "desc": "",
                    "venue": "",
                    "registration": "详见活动链接",
                }

            # 确定活动状态
            now = datetime.now()
            if detail["date_info"]:
                y, m, d = detail["date_info"]
                event_date = datetime(y, m, d)
                if event_date < now:
                    status = "completed"
                    status_label = "已举办"
                else:
                    status = "upcoming"
                    status_label = "即将举办"
            else:
                status = "upcoming"
                status_label = "即将举办"

            event = {
                "title": detail["title"],
                "organizer": source_name,
                "type": "forum",
                "typeLabel": "论坛",
                "topics": _guess_topics(link_text + " " + detail["desc"]),
                "status": status,
                "statusLabel": status_label,
                "priority": "medium",
                "desc": detail["desc"],
                "url": link_url,
                "venue": detail["venue"],
                "registration": detail["registration"],
            }
            if detail["date_info"]:
                event["year"], event["month"], event["day"] = detail["date_info"]
            else:
                event["year"] = now.year
                event["month"] = now.month
                event["day"] = now.day

            found_events.append(event)
            time.sleep(1)  # 详情页之间也加延迟

        time.sleep(REQUEST_DELAY)

    return found_events


def _guess_topics(text):
    """根据文本猜测议题标签。"""
    topics = []
    topic_keywords = {
        "digital": ["数字经济", "AI", "人工智能", "数字化", "数字贸易", "数据"],
        "compliance": ["合规", "跨境", "法律", "风控", "监管"],
        "tax": ["税务", "税收", "财税", "BEPS", "CRS", "转让定价"],
        "supply": ["供应链", "采购", "物流", "产业链"],
        "general": ["出海", "全球化", "国际", "海外", "走出去"],
    }
    for topic, kws in topic_keywords.items():
        if any(kw in text for kw in kws):
            topics.append(topic)
    if not topics:
        topics.append("general")
    return topics


def scrape_all_sources():
    """抓取所有来源，返回所有发现的活动列表。"""
    all_events = []
    for source in SOURCES:
        logger.info("=" * 60)
        logger.info("开始抓取来源: %s", source["name"])
        try:
            events = scrape_source(source)
            all_events.extend(events)
            logger.info("来源 [%s] 发现 %d 个活动", source["name"], len(events))
        except Exception as e:
            logger.error("来源 [%s] 抓取出错: %s", source["name"], e)
        time.sleep(REQUEST_DELAY)
    return all_events
