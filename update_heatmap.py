import os
import html
from pathlib import Path
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from calendar import monthrange
from notion_client import Client

DATA_SOURCE_ID = "2d345d2d-dce6-802c-86ff-000b746e3b43"
TODAY = datetime.now(ZoneInfo("Asia/Shanghai")).date()
YEAR = TODAY.year
MONTH = TODAY.month
CATEGORIES = ["书籍", "影视", "游戏", "做饭", "厨具"]
COLORS = [
    "#ebedf0", "#fff4b8", "#b7d8ff",
    "#ffc48a", "#d7b5ff", "#b7e4c7",
    "#ff9c9c", "#c8a18a", "#242424"
]


def color_for(count):
    return COLORS[min(count, len(COLORS) - 1)]


token = os.environ.get("NOTION_TOKEN")
if not token:
    raise SystemExit("缺少 NOTION_TOKEN 环境变量")

notion = Client(auth=token)
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
grid_end = last_day + timedelta(days=(5 - last_day.weekday()) % 7 + 1)
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
            f'<span class="cell" style="background:{color_for(count)}" '
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
        f'<span class="legend-cell" style="background:{color_for(i)}"></span>'
        for i in range(len(COLORS))
    )
    return f'''<section class="panel year-panel">
      <h2>{YEAR} 年总打卡 · 全年</h2>
      <div class="scroll year-scroll">
        <div class="month-labels" style="grid-template-columns:repeat({week_count},16px)">{''.join(month_labels)}</div>
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
            f'<span class="month-day" style="background:{color_for(count)}" '
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


# 首页仅放年度总打卡长热力图。
year_section = make_year_heatmap()
write_page(
    f"{YEAR} 年总打卡热力图",
    f'<h1>{YEAR} 年总打卡热力图</h1><div class="summary">年度记录数：{record_count} 条。悬停方格可查看每天各类别的打卡详情。</div>{year_section}',
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
    write_page(
        f"{category}打卡热力图",
        f'<h1>{html.escape(category)}打卡热力图</h1><div class="summary">显示当前月份（{YEAR}年{MONTH}月）；悬停方格可查看当天详情。</div>{section}',
        f"{CATEGORY_PATHS[category]}/index.html",
    )

print(f"已生成年度总打卡图及 {len(CATEGORIES)} 个分类月度页面，共统计 {record_count} 条记录；分类小图为 {YEAR} 年 {MONTH} 月。")
