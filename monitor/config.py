"""
监控看板全局配置
"""
import os

# ===== 路径配置 =====
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_HTML = os.path.join(BASE_DIR, "index.html")
DATA_JSON = os.path.join(BASE_DIR, "data", "events.json")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Git 自动推送配置
GIT_AUTO_PUSH = True  # 设为 False 则不自动推送
GIT_COMMIT_MSG = "自动更新: {date} 监控数据"

# ===== 关键词 (用于匹配活动标题/链接文本) =====
KEYWORDS = [
    "出海", "跨境", "对外投资", "走出去", "数字经济",
    "国际合作", "经贸对接", "跨境合规", "出海税务",
    "供应链", "全球化", "服贸会", "数字贸易",
    "外资", "外商投资", "一带一路", "出海基地",
    "涉外", "海外", "国际论坛", "对接会"
]

# ===== 监控来源配置 =====
# 每个来源包含: name, url(主页), pages(需抓取的列表页), type, focus
SOURCES = [
    {
        "name": "北京市商务局",
        "url": "https://sw.beijing.gov.cn",
        "pages": [
            "https://sw.beijing.gov.cn/xwdt/",
            "https://sw.beijing.gov.cn/zwgk/tzgg/",
        ],
        "type": "政府机关",
        "focus": "走出去系列活动、经贸对接、对外投资政策",
    },
    {
        "name": "中关村管委会（市科委）",
        "url": "https://kw.beijing.gov.cn",
        "pages": [
            "https://kw.beijing.gov.cn/xwdt/kcyx/",
            "https://kw.beijing.gov.cn/zwgk/tzgg/",
        ],
        "type": "政府机关",
        "focus": "科创出海会客厅、中关村论坛系列、人才政策",
    },
    {
        "name": "北京CBD管委会",
        "url": "http://www.bjchy.gov.cn",
        "pages": [
            "http://www.bjchy.gov.cn/dynamic/news/",
        ],
        "type": "政府机关",
        "focus": "CBD论坛年会、跨境投资论坛、法商融合示范区",
    },
    {
        "name": "北京市经信局",
        "url": "https://jxj.beijing.gov.cn",
        "pages": [
            "https://jxj.beijing.gov.cn/jxdt/gzdt/",
            "https://jxj.beijing.gov.cn/jxdt/tzgg/",
        ],
        "type": "政府机关",
        "focus": "数字经济出海政策、出海十条、出海基地",
    },
    {
        "name": "德勤中国 (Deloitte)",
        "url": "https://www2.deloitte.com",
        "pages": [
            "https://www2.deloitte.com/cn/zh/pages/about-deloitte/topics/press-releases.html",
        ],
        "type": "咨询机构",
        "focus": "IPO市场报告、出海税务研讨、科技企业评选",
    },
    {
        "name": "毕马威中国 (KPMG)",
        "url": "https://kpmg.com",
        "pages": [
            "https://kpmg.com/cn/zh/home/media/press-releases.html",
            "https://kpmg.com/cn/zh/home/insights.html",
        ],
        "type": "咨询机构",
        "focus": "出海税务培训、AI商业化、跨境合规方案",
    },
    {
        "name": "中欧国际工商学院",
        "url": "https://www.ceibs.edu",
        "pages": [
            "https://www.ceibs.edu/events",
            "https://www.ceibs.edu/news",
        ],
        "type": "智库/教育",
        "focus": "智荟中欧论坛、企业全球化选择、跨境布局",
    },
    {
        "name": "全球化智库 (CCG)",
        "url": "https://www.ccg.org.cn",
        "pages": [
            "https://www.ccg.org.cn/",
        ],
        "type": "智库",
        "focus": "中国企业出海交流大会、政策研究、资源对接",
    },
    {
        "name": "服贸会组委会",
        "url": "https://www.ciftis.org",
        "pages": [
            "https://www.ciftis.org/",
        ],
        "type": "展会平台",
        "focus": "服务贸易、数字贸易、服务出海专题论坛",
    },
]

# ===== HTTP 请求配置 =====
REQUEST_TIMEOUT = 30  # 秒
REQUEST_DELAY = 2  # 每个来源之间的延迟(秒)，避免被封锁
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

# ===== 议题标签映射 =====
TOPIC_LABELS = {
    "digital": "数字经济",
    "compliance": "跨境合规",
    "tax": "海外税务",
    "supply": "供应链重塑",
    "general": "综合出海",
}

# Excel 导出字段
EXPORT_FIELDS = [
    "活动名称", "日期", "主办单位", "类型", "议题",
    "状态", "举办地址", "报名方式", "详情链接",
]

# 已知活动举办地址 (id -> venue)，与 HTML 中的 venueMap 保持一致
VENUE_MAP = {
    3: "中关村综保区科创出海会客厅",
    7: "香港",
    11: "中关村丰台园",
    14: "海淀园",
    15: "上海财经大学",
    16: "上海（世界人工智能大会）",
    17: "中关村展示中心",
    18: "北京经开区",
    19: "首钢园",
    21: "香港会议展览中心",
}
