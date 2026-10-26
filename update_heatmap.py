import os
import html
from pathlib import Path
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from calendar import monthrange
from notion_client import Client

DATA_SOURCE_ID = "2d345d2d-dce6-802c-86ff-000b746e3b43"
COMPLETION_SOURCES = {
    "阅读完成": {
        "id": "1d145d2d-dce6-801c-aaba-000be2385582",
        "property": "已读完计数",
        "date_property": "结束日期",
        "color": "#268A48",
        "unit": "本",
        "emoji": "📚",
    },
    "观看完毕": {
        "id": "2d345d2d-dce6-818e-a4fc-000bb97539f5",
        "property": "已看完计数",
        "date_property": "结束日期",
        "color": "#7038C8",
        "unit": "部",
        "emoji": "🎬",
    },
    "游戏通关": {
        "id": "eb545d2d-dce6-824d-a120-87c95c8ed2aa",
        "property": "已通关计数",
        "date_property": "结束日期",
        "color": "#2169BF",
        "unit": "个",
        "emoji": "🎮",
    },
}
TODAY = datetime.now(ZoneInfo("Asia/Shanghai")).date()
YEAR = TODAY.year
MONTH = TODAY.month
CATEGORIES = ["书籍", "影视", "游戏", "做饭", "厨具"]
# 总热力图：15 格
# 白、浅灰、蓝1-2、绿3-4、黄5-6、橙7-8、红9-10、紫11-12、黑
TOTAL_COLORS = [
    "#F2F2F2",
    "#EAF3FF", "#D6E7FF", "#BFD9FF",
    "#BDE5CA", "#A0D8B3",
    "#FFDC60", "#F6CE40",
    "#ED793A", "#DA642C",
    "#B32E3C", "#972333",
    "#441F7D", "#34165F",
    "#000000"
]

# 五张分类月度热力图：各 9 格
CATEGORY_COLORS = {
    "书籍": [
        "#EBEDF0", "#E2F5E8", "#BFE8CD",
        "#91D6A8", "#65C681", "#3EAD61",
        "#268A48", "#176B36", "#0B4825"
    ],
    "影视": [
        "#EBEDF0", "#F0E5FF", "#DCC5FF",
        "#C5A0FF", "#AA7BFA", "#8B55E8",
        "#7038C8", "#54259F", "#35166B"
    ],
    "游戏": [
        "#EBEDF0", "#E0F0FF", "#B9DEFF",
        "#8BC5FF", "#5BA8F5", "#3488E0",
        "#2169BF", "#174D96", "#103366"
    ],
    "做饭": [
        "#EBEDF0", "#FFF9D9", "#FFF0A3",
        "#FFE16B", "#FFCF3F", "#F5B51B",
        "#E99A0C", "#CF7508", "#A84E08"
    ],
    "厨具": [
        "#EBEDF0", "#FFE8F0", "#FFC9DD",
        "#FFA4C8", "#F77EAF", "#E85C98",
        "#D43D80", "#B52667", "#8C174D"
    ]
}


# 五个统计首页：页面 ID 与累计属性
STATS_PAGES = {
    "书籍": {
        "id": "3f645d2d-dce6-80a3-a6c0-c2e6c160399d",
        "title": "📚 阅读统计",
        "label": "阅读",
        "icon": "📖",
        "color": "#268A48",
        "colors": ["#268A48", "#46965D", "#72B584"],
        "light_colors": ["#65A978", "#7FBD8D", "#9ACDA5"],
        "duration": "总阅读时长显示",
        "day_length": "总阅读天长",
        "count": "总阅读次数",
        "days_display": "总阅读天数显示",
        "minutes": "总阅读分钟",
        "days": "总阅读天数",
    },
    "影视": {
        "id": "54a45d2d-dce6-8349-b662-81d20512ec50",
        "title": "📺 观影统计",
        "label": "观看",
        "icon": "🎞️",
        "color": "#7038C8",
        "colors": ["#7038C8", "#8559D0", "#9B7BDD"],
        "light_colors": ["#A58ADE", "#B39BE3", "#C1AFE8"],
        "duration": "总观影时长显示",
        "day_length": "总观影天长",
        "count": "总观影次数",
        "days_display": "总观影天数显示",
        "minutes": "总观影分钟",
        "days": "总观影天数",
    },
    "游戏": {
        "id": "3fa45d2d-dce6-80ea-ac3f-f31b8c61c0b4",
        "title": "🕹️ 游戏统计",
        "label": "玩了",
        "icon": "🎮",
        "color": "#2169BF",
        "colors": ["#2169BF", "#407FC7", "#6599D3"],
        "light_colors": ["#72A5DE", "#8CB4E2", "#A6C5E8"],
        "duration": "总游戏时长显示",
        "day_length": "总游戏天长",
        "count": "总游戏次数",
        "days_display": "总游戏天数显示",
        "minutes": "总游戏分钟",
        "days": "总游戏天数",
    },
    "做饭": {
        "id": "1e845d2d-dce6-83f9-b5ea-81fbd1e3a710",
        "title": "🥘 做饭统计",
        "label": "做饭",
        "icon": "🍳",
        "color": "#9B7400",
        "colors": ["#9B7400", "#AE8718", "#C09E36"],
        "light_colors": ["#C5A43E", "#D0B45C", "#D8C47E"],
        "duration": "总做饭时长显示",
        "day_length": "总做饭天长",
        "count": "总做饭次数",
        "days_display": "总做饭天数显示",
        "minutes": "总做饭分钟",
        "days": "总做饭天数",
    },
    "厨具": {
        "id": "94045d2d-dce6-836c-a933-81975edf9fd6",
        "title": "🍴 厨具使用统计",
        "label": "厨具使用",
        "icon": "🍽️",
        "color": "#C04485",
        "colors": ["#C04485", "#CD6098", "#D985AF"],
        "light_colors": ["#D986B0", "#E19CBD", "#E8B8D0"],
        "duration": "总厨具使用时长显示",
        "day_length": "总厨具使用天长",
        "count": "总厨具使用次数",
        "days_display": "总厨具使用天数显示",
        "minutes": "总厨具使用分钟",
        "days": "总厨具使用天数",
    },
}


def read_notion_property(prop):
    """把 Notion 属性转换为可显示的值。"""
    if not prop:
        return ""

    prop_type = prop.get("type")

    if prop_type in ("title", "rich_text"):
        items = prop.get(prop_type, [])
        return "".join(item.get("plain_text", "") for item in items)

    if prop_type == "number":
        value = prop.get("number")
        return str(value) if value is not None else ""

    if prop_type == "formula":
        formula = prop.get("formula", {})
        value = formula.get("string")
        if value is not None:
            return str(value)
        value = formula.get("number")
        return str(value) if value is not None else ""

    if prop_type == "rollup":
        rollup = prop.get("rollup", {})
        value = rollup.get("number")
        if value is not None:
            return str(value)
        items = rollup.get("array", [])
        return "".join(read_notion_property(item) for item in items)

    return ""


def format_duration(minutes):
    """把分钟数格式化为 x天x小时x分钟。"""
    minutes = max(0, int(minutes))
    days, remainder = divmod(minutes, 1440)
    hours, mins = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if mins or not parts:
        parts.append(f"{mins}分钟")

    return "".join(parts)


def format_hours_minutes(minutes):
    """把分钟数格式化为 x小时x分钟，不显示天数。"""
    minutes = max(0, int(minutes))
    hours, mins = divmod(minutes, 60)
    return f"{hours}小时{mins}分钟"



def get_page_stats(database_id):
    """读取统计数据库中第一条统计记录的属性值。"""
    result = notion.data_sources.query(
        data_source_id=database_id,
        page_size=100,
    )

    pages = result.get("results", [])

    if not pages:
        raise ValueError(
            f"统计数据库 {database_id} 中没有记录，无法读取累计统计。"
        )

    if len(pages) > 1:
        raise ValueError(
            f"统计数据库 {database_id} 中有多条记录，"
            "请先确认应该读取哪一条统计记录。"
        )

    return pages[0].get("properties", {})


def make_category_stats(category):
    """生成分类热力图下方的至今、当年、当月统计。"""
    config = STATS_PAGES[category]
    props = get_page_stats(config["id"])

    def existing_value(key, fallback="0"):
        value = read_notion_property(props.get(config[key]))
        return value if value != "" else fallback

    # 至今：直接读取统计首页中已计算好的累计值
    all_time_duration = existing_value("day_length")
    all_time_days = existing_value("days_display")
    all_time_count = existing_value("count")
    all_time_hours = existing_value("duration")
    all_time_minutes = existing_value("minutes")

    # 当年与当月：按日志开始时间筛选，使用结束时间计算时长
    periods = {
        "year": {
            "label": f"{YEAR}年{config['label']}{config['icon']}",
            "start": date(YEAR, 1, 1),
            "end": date(YEAR + 1, 1, 1),
        },
        "month": {
            "label": f"{MONTH}月{config['label']}{config['icon']}",
            "start": date(YEAR, MONTH, 1),
            "end": (
                date(YEAR + 1, 1, 1)
                if MONTH == 12
                else date(YEAR, MONTH + 1, 1)
            ),
        },
    }

    stats = {}
    for period_name, period in periods.items():
        stats[period_name] = {
            "minutes": 0,
            "count": 0,
            "days": set(),
        }

    cursor = None
    while True:
        args = {
            "data_source_id": DATA_SOURCE_ID,
            "page_size": 100,
        }
        if cursor:
            args["start_cursor"] = cursor

        result = notion.data_sources.query(**args)

        for page in result["results"]:
            page_props = page.get("properties", {})
            selected = page_props.get("类别", {}).get("select")
            log_category = selected.get("name") if selected else ""

            if log_category != category:
                continue

            start_info = page_props.get("开始时间", {}).get("date")
            end_info = page_props.get("结束时间", {}).get("date")

            if not start_info or not start_info.get("start"):
                continue
            if not end_info or not end_info.get("start"):
                continue

            start_text = start_info["start"]
            end_text = end_info["start"]

            try:
                start_dt = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_text.replace("Z", "+00:00"))

                # 统一时区后计算实际分钟数
                if start_dt.tzinfo is not None:
                    start_dt = start_dt.astimezone(ZoneInfo("Asia/Shanghai"))
                if end_dt.tzinfo is not None:
                    end_dt = end_dt.astimezone(ZoneInfo("Asia/Shanghai"))

                start_day = start_dt.date()
                duration_minutes = max(
                    0, int((end_dt - start_dt).total_seconds() // 60)
                )
            except (ValueError, TypeError):
                continue

            for period_name, period in periods.items():
                if period["start"] <= start_day < period["end"]:
                    stats[period_name]["minutes"] += duration_minutes
                    stats[period_name]["count"] += 1
                    stats[period_name]["days"].add(start_day)

        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")

    groups = [
        {
            "label": f"至今{config['label']}{config['icon']}",
            "duration": all_time_duration,
            "days": all_time_days,
            "count": all_time_count,
            "hours": all_time_hours,
            "minutes": all_time_minutes,
        }
    ]

    for period_name in ("year", "month"):
        period_stats = stats[period_name]
        minutes = period_stats["minutes"]
        groups.append({
            "label": periods[period_name]["label"],
            "duration": format_duration(minutes),
            "days": f"{len(period_stats['days'])}天",
            "count": f"{period_stats['count']}次",
            "hours": format_hours_minutes(minutes),
            "minutes": f"{minutes}分钟",
        })

    rows = []
    for index, group in enumerate(groups):
        rows.append(
            f'<div class="stat-row">'
            f'<div class="stat-label" style="color:{config["colors"][index]}">'
            f'{html.escape(group["label"])}'
            f'</div>'
            f'<div class="stat-values">'
            f'<div class="stat-main" style="color:{config["colors"][index]}">'
            f'{html.escape(str(group["duration"]))} · '
            f'{html.escape(str(group["days"]))} · '
            f'{html.escape(str(group["count"]))}'
            f'</div>'
            f'<div class="stat-sub" style="color:{config["light_colors"][index]}">'
            f'{html.escape(str(group["hours"]))} · '
            f'{html.escape(str(group["minutes"]))}'
            f'</div>'
            f'</div>'
            f'</div>'
        )

    return (
        f'<section class="panel category-stats">'
        f'<h2 style="color:{config["color"]}">{config["title"]}</h2>'
        f'{"".join(rows)}'
        f'</section>'
    )

def total_color_for(count):
    return TOTAL_COLORS[min(count, len(TOTAL_COLORS) - 1)]


def category_color_for(category, count):
    colors = CATEGORY_COLORS[category]
    return colors[min(count, len(colors) - 1)]


token = os.environ.get("NOTION_TOKEN")
if not token:
    raise SystemExit("缺少 NOTION_TOKEN 环境变量")

notion = Client(auth=token)
def get_completion_counts(data_source_id, property_name, date_property):
    total = 0
    year_total = 0
    cursor = None

    while True:
        args = {
            "data_source_id": data_source_id,
            "page_size": 100,
        }
        if cursor:
            args["start_cursor"] = cursor

        result = notion.data_sources.query(**args)

        for page in result["results"]:
            props = page.get("properties", {})

            # 累计完成数量：继续使用原有的 0/1 公式属性
            formula = props.get(property_name, {}).get("formula", {})
            number = formula.get("number")
            if number is not None:
                total += number

            # 当年完成数量：只统计结束日期属于当前年份的记录
            date_info = props.get(date_property, {}).get("date")
            end_date = date_info.get("start") if date_info else None
            if end_date and end_date[:4] == str(YEAR):
                if number is not None:
                    year_total += number

        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")

    return total, year_total


completion_counts = {}
for name, source in COMPLETION_SOURCES.items():
    total, year_total = get_completion_counts(
        source["id"],
        source["property"],
        source["date_property"],
    )
    completion_counts[name] = {
        "total": total,
        "year": year_total,
    }
daily = defaultdict(lambda: {"总计": 0, **{name: 0 for name in CATEGORIES}})
record_count = 0
cursor = None

try:
    while True:
        args = {"data_source_id": DATA_SOURCE_ID, "page_size": 100}
        if cursor:
            args["start_cursor"] = cursor
        result = notion.data_sources.query(**args)

        for page in result["results"]:
            props = page.get("properties", {})
            date_info = props.get("开始时间", {}).get("date")
            if not date_info or not date_info.get("start"):
                continue
            day_text = date_info["start"][:10]
            if not day_text.startswith(str(YEAR)):
                continue
            selected = props.get("类别", {}).get("select")
            category = selected.get("name") if selected else ""
            daily[day_text]["总计"] += 1
            if category in CATEGORIES:
                daily[day_text][category] += 1
            record_count += 1

        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")
except Exception as e:
    raise SystemExit(f"读取 Notion 失败：{e}")


# 年度长热力图：一列一周，按星期日到星期六排列
first_day = date(YEAR, 1, 1)
last_day = date(YEAR, 12, 31)
grid_start = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
grid_end = last_day + timedelta(days=(5 - last_day.weekday()) % 7)
all_dates = []
current = grid_start
while current <= grid_end:
    all_dates.append(current)
    current += timedelta(days=1)
week_count = len(all_dates) // 7


def make_year_heatmap():
    cells = []
    for day in all_dates:
        if day.year != YEAR:
            cells.append('<span class="cell outside"></span>')
            continue
        counts = daily.get(day.isoformat(), {})
        count = counts.get("总计", 0)
        detail = "；".join(f"{name} {counts.get(name, 0)} 次" for name in CATEGORIES)
        tip = f"{day.isoformat()}｜总计 {count} 次｜{detail}"
        cells.append(
            f'<span class="cell" style="background:{total_color_for(count)}" '
            f'title="{html.escape(tip, quote=True)}"></span>'
        )

    month_labels = []
    for month in range(1, 13):
        month_day = date(YEAR, month, 1)
        week_index = (month_day - grid_start).days // 7 + 1
        month_labels.append(
            f'<span style="grid-column:{week_index}">{month}月</span>'
        )

    legend = ''.join(
        f'<span class="legend-cell" style="background:{total_color_for(i)}"></span>'
        for i in range(len(TOTAL_COLORS))
    )
    return f'''<section class="panel year-panel">
      <h2>{YEAR} 年总打卡 · 全年</h2>
      <div class="scroll year-scroll">
        <div class="month-labels" style="grid-template-columns:repeat({week_count},13px)">{''.join(month_labels)}</div>
        <div class="heatmap year-heatmap" style="grid-template-columns:repeat({week_count},13px)">{''.join(cells)}</div>
      </div>
      <p class="legend">少 ← {legend} → 多</p>
    </section>'''


def make_month_heatmap(category):
    first = date(YEAR, MONTH, 1)
    days_in_month = monthrange(YEAR, MONTH)[1]
    # Monday-first monthly calendar: 7 columns, up to 6 rows
    offset = first.weekday()
    cells = []
    for _ in range(offset):
        cells.append('<span class="cell outside"></span>')
    month_total = 0
    for day_number in range(1, days_in_month + 1):
        day = date(YEAR, MONTH, day_number)
        counts = daily.get(day.isoformat(), {})
        count = counts.get(category, 0)
        month_total += count
        tip = f"{day.isoformat()}｜{category} {count} 次｜当天总计 {counts.get('总计', 0)} 次"
        cells.append(
            f'<span class="month-day" style="background:{category_color_for(category, count)}" '
            f'title="{html.escape(tip, quote=True)}"><span class="day-number">{day_number}</span></span>'
        )
    while len(cells) % 7:
        cells.append('<span class="cell outside"></span>')

    return f'''<section class="panel month-panel">
      <h2>{html.escape(category)} · {YEAR}年{MONTH}月</h2>
      <div class="weekday-row"><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span></div>
      <div class="month-grid">{''.join(cells)}</div>
      <p class="month-summary">本月打卡：{month_total} 次</p>
    </section>'''


# 共用样式：总打卡年度图与分类月度图分别生成独立网页，便于分别嵌入 Notion。
COMMON_STYLE = r"""
* { box-sizing: border-box; }
body { margin: 0; padding: 18px; background: #f7f8fa; color: #24292f; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
h1 { font-size: 24px; margin: 0 0 8px; }
.summary { color: #57606a; margin-bottom: 18px; font-size: 13px; }
.completion-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
    margin: 0 0 16px;
    padding: 16px;
    background: white;
    border: 1px solid #d8dee4;
    border-radius: 10px;
}

.completion-item {
    min-width: 0;
}

.completion-title {
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    margin-bottom: 8px;
}

.completion-total {
    font-size: 20px;
    font-weight: 700;
    line-height: 1.4;
    margin-bottom: 3px;
}

.completion-year {
    font-size: 13px;
    font-weight: 500;
    line-height: 1.5;
}
.panel { background: white; border: 1px solid #d8dee4; border-radius: 12px; padding: 16px; margin: 0; }
h2 { font-size: 18px; margin: 0 0 14px; }
.scroll { overflow-x: auto; padding: 2px 2px 8px; }
.month-labels { display: grid; height: 30px; align-items: start; font-size: 11px; line-height: 16px; color: #57606a; column-gap: 3px; }
.heatmap { display: grid; grid-template-rows: repeat(7, 13px); grid-auto-flow: column; gap: 3px; width: max-content; }
.cell { width: 13px; height: 13px; border-radius: 3px; border: 1px solid rgba(27,31,36,.06); }
.outside { background: transparent; border-color: transparent; }
.legend { display: flex; align-items: center; gap: 4px; color: #57606a; font-size: 11px; margin: 14px 0 0; }
.legend-cell { display: inline-block; width: 12px; height: 12px; border-radius: 3px; }
.weekday-row, .month-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 5px; }
.weekday-row { margin-bottom: 7px; color: #57606a; font-size: 12px; text-align: center; }
.month-day { position: relative; aspect-ratio: 1; min-width: 0; border-radius: 5px; border: 1px solid rgba(27,31,36,.06); display: flex; align-items: center; justify-content: center; }
.day-number { font-size: 11px; color: #24292f; opacity: .85; }
.month-summary { font-size: 12px; color: #57606a; margin: 12px 0 0; }

.category-stats {
    margin-top: 12px;
}

.category-stats h2 {
    margin-bottom: 16px;
}

.stat-row {
    display: grid;
    grid-template-columns: 148px minmax(0, 1fr);
    column-gap: 12px;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid #f0f1f3;
}

.stat-row:last-child {
    border-bottom: none;
    padding-bottom: 0;
}

.stat-label {
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
}

.stat-values {
    min-width: 0;
}

.stat-main {
    font-size: 14px;
    line-height: 1.7;
    font-weight: 500;
    overflow-wrap: anywhere;
}

.stat-sub {
    font-size: 12px;
    line-height: 1.6;
    overflow-wrap: anywhere;
}

@media (max-width: 480px) {
    .stat-row {
        grid-template-columns: 116px minmax(0, 1fr);
        column-gap: 8px;
    }

    .stat-label {
        font-size: 12px;
    }

    .stat-main {
        font-size: 12px;
    }

    .stat-sub {
        font-size: 11px;
    }
}

footer { color: #57606a; font-size: 12px; margin-top: 18px; }
"""


def write_page(title, body_content, filename):
    document = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{COMMON_STYLE}</style>
</head>
<body>
{body_content}
<footer>由 Notion 打卡数据生成 · 页面每日自动更新</footer>
</body>
</html>'''
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    Path(filename).write_text(document, encoding="utf-8")


# 首页显示完成数量和年度总打卡长热力图。
year_section = make_year_heatmap()

completion_html = '<div class="completion-stats">'
for name, source in COMPLETION_SOURCES.items():
    counts = completion_counts[name]
    total = counts["total"]
    year_total = counts["year"]

    # 当年数字使用同色系的浅色
    year_color = {
        "阅读完成": "#65B77E",
        "观看完毕": "#A58ADE",
        "游戏通关": "#72A5DE",
    }[name]

    completion_html += (
        f'<div class="completion-item">'
        f'<div class="completion-title" style="color:{source["color"]}">'
        f'{source["emoji"]} {name}'
        f'</div>'
        f'<div class="completion-total" style="color:{source["color"]}">'
        f'{total}{source["unit"]}'
        f'</div>'
        f'<div class="completion-year" style="color:{year_color}">'
        f'{YEAR} · {year_total}{source["unit"]}'
        f'</div>'
        f'</div>'
    )
completion_html += '</div>'
write_page(
    f"{YEAR} 年总打卡热力图",
    f'<h1>{YEAR} 年总打卡热力图</h1><div class="summary">年度记录数：{record_count} 条。悬停方格可查看每天各类别的打卡详情。</div>{completion_html}{year_section}',
    "index.html",
)

# 每个分类各自生成一个独立的月度热力图页面，供 Notion 分开嵌入。
CATEGORY_PATHS = {
    "书籍": "books",
    "影视": "media",
    "游戏": "games",
    "做饭": "cooking",
    "厨具": "kitchenware",
}

for category in CATEGORIES:
    section = make_month_heatmap(category)
    stats_section = make_category_stats(category)
    write_page(
        f"{category}打卡热力图",
        f'<h1>{html.escape(category)}打卡热力图</h1>'
        f'<div class="summary">显示当前月份（{YEAR}年{MONTH}月）；悬停方格可查看当天详情。</div>'
        f'{section}{stats_section}',
        f"{CATEGORY_PATHS[category]}/index.html",
    )


print(f"已生成年度总打卡图及 {len(CATEGORIES)} 个分类月度页面，共统计 {record_count} 条记录；分类小图为 {YEAR} 年 {MONTH} 月。")
