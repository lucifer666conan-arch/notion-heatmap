
import os
import html
from pathlib import Path
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from notion_client import Client

DATA_SOURCE_ID = "2d345d2d-dce6-802c-86ff-000b746e3b43"
YEAR = datetime.now(ZoneInfo("Asia/Shanghai")).year

CATEGORIES = ["书籍", "影视", "游戏", "做饭", "厨具"]

COLORS = [
    "#ebedf0", "#fff4b8", "#b7d8ff",
    "#ffc48a", "#d7b5ff", "#b7e4c7",
    "#ff9c9c", "#c8a18a", "#242424"
]

token = os.environ.get("NOTION_TOKEN")
if not token:
    raise SystemExit("缺少 NOTION_TOKEN 环境变量")

notion = Client(auth=token)

daily = defaultdict(lambda: {
    "总计": 0,
    **{name: 0 for name in CATEGORIES}
})

cursor = None
record_count = 0

try:
    while True:
        args = {
            "data_source_id": DATA_SOURCE_ID,
            "page_size": 100
        }
        if cursor:
            args["start_cursor"] = cursor

        result = notion.data_sources.query(**args)

        for page in result["results"]:
            props = page.get("properties", {})
            date_info = props.get("开始时间", {}).get("date")

            if not date_info or not date_info.get("start"):
                continue

            day = date_info["start"][:10]
            if not day.startswith(str(YEAR)):
                continue

            selected = props.get("类别", {}).get("select")
            category = selected.get("name") if selected else ""

            daily[day]["总计"] += 1
            if category in CATEGORIES:
                daily[day][category] += 1

            record_count += 1

        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")

except Exception as e:
    raise SystemExit(f"读取 Notion 失败：{e}")


first_day = date(YEAR, 1, 1)
last_day = date(YEAR, 12, 31)
grid_start = first_day - timedelta(
    days=(first_day.weekday() + 1) % 7
)
grid_end = last_day + timedelta(
    days=(5 - last_day.weekday()) % 7 + 1
)

all_dates = []
current = grid_start
while current <= grid_end:
    all_dates.append(current)
    current += timedelta(days=1)

week_count = len(all_dates) // 7


def make_heatmap(title, key):
    cells = []

    for day in all_dates:
        if day.year != YEAR:
            cells.append('<span class="cell outside"></span>')
            continue

        day_text = day.isoformat()
        counts = daily.get(day_text, {})
        count = counts.get(key, 0)
        level = min(count, 8)

        if key == "总计":
            detail = "；".join(
                f"{name} {counts.get(name, 0)} 次"
                for name in CATEGORIES
            )
            tip = f"{day_text}｜总计 {count} 次｜{detail}"
        else:
            tip = (
                f"{day_text}｜{title} {count} 次｜"
                f"当天总计 {counts.get('总计', 0)} 次"
            )

        cells.append(
            f'<span class="cell" '
            f'style="background:{COLORS[level]}" '
            f'title="{html.escape(tip, quote=True)}"></span>'
        )

    month_labels = []
    for month in range(1, 13):
        month_day = date(YEAR, month, 1)
        week_index = (month_day - grid_start).days // 7 + 1
        month_labels.append(
            f'<span style="grid-column:{week_index}">{month}月</span>'
        )

    legend = "".join(
        f'<span class="legend-cell" style="background:{c}"></span>'
        for c in COLORS
    )

    return f"""
    <section class="panel">
      <h2>{html.escape(title)}</h2>
      <div class="scroll">
        <div class="month-labels"
             style="grid-template-columns:repeat({week_count},13px)">
          {''.join(month_labels)}
        </div>
        <div class="heatmap"
             style="grid-template-columns:repeat({week_count},13px)">
          {''.join(cells)}
        </div>
      </div>
      <p class="legend">少 ← {legend} → 多</p>
    </section>
    """


sections = [make_heatmap("总打卡", "总计")]
sections.extend(make_heatmap(name, name) for name in CATEGORIES)

page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{YEAR} 年打卡热力图</title>
<style>
* {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 24px;
  background: #f7f8fa; color: #24292f;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}}
h1 {{ font-size: 26px; margin-bottom: 8px; }}
.summary {{ color: #57606a; margin-bottom: 24px; }}
.panel {{
  background: white; border: 1px solid #d8dee4;
  border-radius: 12px; padding: 18px;
  margin: 16px 0; max-width: 100%;
}}
h2 {{ font-size: 18px; margin: 0 0 16px; }}
.scroll {{ overflow-x: auto; padding-bottom: 8px; }}
.month-labels {{
  display: grid; height: 22px;
  font-size: 11px; color: #57606a;
}}
.heatmap {{
  display: grid;
  grid-template-rows: repeat(7, 13px);
  grid-auto-flow: column;
  gap: 3px; width: max-content;
}}
.cell {{
  width: 13px; height: 13px; border-radius: 3px;
  border: 1px solid rgba(27,31,36,.06);
}}
.outside {{ background: transparent; border-color: transparent; }}
.legend {{
  display: flex; align-items: center; gap: 4px;
  color: #57606a; font-size: 11px; margin: 14px 0 0;
}}
.legend-cell {{
  display: inline-block; width: 12px; height: 12px;
  border-radius: 3px;
}}
footer {{ color: #57606a; font-size: 12px; margin-top: 24px; }}
</style>
</head>
<body>
<h1>{YEAR} 年打卡热力图</h1>
<div class="summary">
  年度记录数：{record_count} 条。
  颜色按每天的打卡次数变化；悬停方格可查看详情。
</div>
{''.join(sections)}
<footer>由 Notion 打卡数据生成</footer>
</body>
</html>
"""

Path("index.html").write_text(page, encoding="utf-8")
print(f"已生成 {YEAR} 年热力图，统计 {record_count} 条记录。")
