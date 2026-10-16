import os
import html
from pathlib import Path
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from calendar import monthrange
from notion_client import Client

SOURCE_DATA_SOURCE_ID = "2d345d2d-dce6-802c-86ff-000b746e3b43"
ARCHIVE_DATABASE_ID = os.environ.get("NOTION_ARCHIVE_DATABASE_ID")
ARCHIVE_PAGE_ID = ARCHIVE_DATABASE_ID

def get_archive_data_source_id():
    blocks = notion.blocks.children.list(
        block_id=ARCHIVE_PAGE_ID,
        page_size=100
    )
    for block in blocks.get("results", []):
        if block.get("type") == "child_database":
            database = notion.databases.retrieve(
                database_id=block["id"]
            )
            sources = database.get("data_sources", [])
            if sources:
                return sources[0]["id"]
   raise SystemExit("没有在历史热力图档案页面中找到数据库数据源")

TOKEN = os.environ.get("NOTION_TOKEN")
BASE_URL = "https://lucifer666conan-arch.github.io/notion-heatmap"
CATEGORIES = ["书籍", "影视", "游戏", "做饭", "厨具"]
CATEGORY_PATHS = {"书籍": "books", "影视": "media", "游戏": "games", "做饭": "cooking", "厨具": "kitchenware"}
COLORS = ["#ebedf0", "#fff4b8", "#b7d8ff", "#ffc48a", "#d7b5ff", "#b7e4c7", "#ff9c9c", "#c8a18a", "#242424"]
TODAY = datetime.now(ZoneInfo("Asia/Shanghai")).date()

if not TOKEN:
    raise SystemExit("缺少 NOTION_TOKEN 环境变量")
if not ARCHIVE_DATABASE_ID:
    raise SystemExit("缺少 NOTION_ARCHIVE_DATABASE_ID 环境变量")
notion = Client(auth=TOKEN)

# 读取完整历史数据，按日期和类别统计。
daily = defaultdict(lambda: {"总计": 0, **{c: 0 for c in CATEGORIES}})
cursor = None
while True:
    args = {"data_source_id": SOURCE_DATA_SOURCE_ID, "page_size": 100}
    if cursor:
        args["start_cursor"] = cursor
    result = notion.data_sources.query(**args)
    for page in result.get("results", []):
        props = page.get("properties", {})
        info = props.get("开始时间", {}).get("date")
        if not info or not info.get("start"):
            continue
        try:
            day_text = info["start"][:10]
            date.fromisoformat(day_text)
        except (ValueError, TypeError):
            continue
        selected = props.get("类别", {}).get("select")
        category = selected.get("name") if selected else ""
        daily[day_text]["总计"] += 1
        if category in CATEGORIES:
            daily[day_text][category] += 1
    if not result.get("has_more"):
        break
    cursor = result.get("next_cursor")

STYLE = r"""
*{box-sizing:border-box}body{margin:0;padding:18px;background:#f7f8fa;color:#24292f;font-family:"Segoe UI","Microsoft YaHei",sans-serif}
h1{font-size:24px;margin:0 0 8px}h2{font-size:18px;margin:0 0 14px}.summary{color:#57606a;margin-bottom:18px;font-size:13px}
.panel{background:white;border:1px solid #d8dee4;border-radius:12px;padding:16px;margin:0}.scroll{overflow-x:auto;padding:2px 2px 8px}
.month-labels{display:grid;height:30px;align-items:start;font-size:11px;line-height:16px;color:#57606a;column-gap:3px}
.heatmap{display:grid;grid-template-rows:repeat(7,13px);grid-auto-flow:column;gap:3px;width:max-content}
.cell{width:13px;height:13px;border-radius:3px;border:1px solid rgba(27,31,36,.06)}.outside{background:transparent;border-color:transparent}
.legend{display:flex;align-items:center;gap:4px;color:#57606a;font-size:11px;margin:14px 0 0}.legend-cell{display:inline-block;width:12px;height:12px;border-radius:3px}
.weekday-row,.month-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px}.weekday-row{margin-bottom:7px;color:#57606a;font-size:12px;text-align:center}
.month-day{position:relative;aspect-ratio:1;min-width:0;border-radius:5px;border:1px solid rgba(27,31,36,.06);display:flex;align-items:center;justify-content:center}
.day-number{font-size:11px;color:#24292f;opacity:.85}.month-summary{font-size:12px;color:#57606a;margin:12px 0 0}footer{color:#57606a;font-size:12px;margin-top:18px}
"""

def write_page(title, body, filename):
    document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style></head><body>{body}<footer>历史热力图档案 · 按归档时的 Notion 打卡数据生成</footer></body></html>'''
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")

def make_year(year):
    first, last = date(year, 1, 1), date(year, 12, 31)
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    end = last + timedelta(days=(5 - last.weekday()) % 7)
    dates, current = [], start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    weeks = len(dates) // 7
    cells = []
    for day in dates:
        if day.year != year:
            cells.append('<span class="cell outside"></span>')
            continue
        counts = daily.get(day.isoformat(), {})
        count = counts.get("总计", 0)
        detail = "；".join(f"{c} {counts.get(c, 0)} 次" for c in CATEGORIES)
        tip = html.escape(f"{day.isoformat()}｜总计 {count} 次｜{detail}", quote=True)
        cells.append(f'<span class="cell" style="background:{COLORS[min(count,len(COLORS)-1)]}" title="{tip}"></span>')
    labels = []
    for m in range(1, 13):
        md = date(year, m, 1)
        col = (md - start).days // 7 + 1
        labels.append(f'<span style="grid-column:{col}">{m}月</span>')
    legend = ''.join(f'<span class="legend-cell" style="background:{c}"></span>' for c in COLORS)
    section = f'<section class="panel"><h2>{year} 年总打卡 · 全年</h2><div class="scroll"><div class="month-labels" style="grid-template-columns:repeat({weeks},13px)">{"".join(labels)}</div><div class="heatmap" style="grid-template-columns:repeat({weeks},13px)">{"".join(cells)}</div></div><p class="legend">少 ← {legend} → 多</p></section>'
    return f'<h1>{year} 年总打卡热力图</h1><div class="summary">年度总打卡记录；悬停方格可查看当天各类别详情。</div>{section}'

def make_month(year, month, category):
    first = date(year, month, 1)
    days = monthrange(year, month)[1]
    cells = ['<span class="cell outside"></span>' for _ in range(first.weekday())]
    total = 0
    for n in range(1, days + 1):
        day = date(year, month, n)
        counts = daily.get(day.isoformat(), {})
        count = counts.get(category, 0)
        total += count
        tip = html.escape(f"{day.isoformat()}｜{category} {count} 次｜当天总计 {counts.get('总计',0)} 次", quote=True)
        cells.append(f'<span class="month-day" style="background:{COLORS[min(count,len(COLORS)-1)]}" title="{tip}"><span class="day-number">{n}</span></span>')
    while len(cells) % 7:
        cells.append('<span class="cell outside"></span>')
    section = f'<section class="panel"><h2>{html.escape(category)} · {year}年{month}月</h2><div class="weekday-row"><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span></div><div class="month-grid">{"".join(cells)}</div><p class="month-summary">本月打卡：{total} 次</p></section>'
    return f'<h1>{html.escape(category)}打卡热力图</h1><div class="summary">{year}年{month}月历史记录；悬停方格可查看当天详情。</div>{section}'


def get_archive_records():
    records = []
    archive_data_source_id = get_archive_data_source_id()
    data_sources = database.get("data_sources", [])
    if not data_sources:
        raise SystemExit("历史热力图档案数据库中没有找到数据源")
    cursor = None
    while True:
        args = {"data_source_id": archive_data_source_id, "page_size": 100}
        if cursor:
            args["start_cursor"] = cursor
        result = notion.data_sources.query(**args)
        records.extend(result.get("results", []))
        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")
    return records


def prop_value(page, name):
    p = page.get("properties", {}).get(name, {})
    if p.get("type") == "number":
        return p.get("number")
    if p.get("type") == "select":
        return (p.get("select") or {}).get("name")
    return None

def set_archive_record(record_map, title, kind, year, month, urls):
    # 历史月份和往年只创建一次；当前月份/当前年度允许随日常打卡更新。
    key = (kind, year, month)
    existing = record_map.get(key)
    is_current = (kind == "年度" and year == TODAY.year) or (kind == "月度" and year == TODAY.year and month == TODAY.month)
    if existing and not is_current:
        return
    properties = {
        "名称": {"title": [{"text": {"content": title}}]},
        "档案类型": {"select": {"name": kind}},
        "年份": {"number": year},
        "月份": {"number": month} if month is not None else {"number": None},
    }
    for name, url in urls.items():
        properties[name] = {"url": url}
    if existing:
        notion.pages.update(page_id=existing["id"], properties=properties)
    else:
       notion.pages.create(parent={"data_source_id": get_archive_data_source_id()}, properties=properties)
# Collect existing records so reruns don't create duplicates.
record_map = {}
for rec in get_archive_records():
    kind = prop_value(rec, "档案类型")
    year = prop_value(rec, "年份")
    month = prop_value(rec, "月份")
    if kind and year is not None:
        record_map[(kind, int(year), int(month) if month is not None else None)] = rec

# Archive every year/month found in source data, plus the current year and month.
years = {date.fromisoformat(d).year for d in daily}
years.add(TODAY.year)
for year in sorted(years):
    year_dir = f"archive/{year}"
    year_record_exists = ("年度", year, None) in record_map
    # 已存在的往年档案保持不动；仅生成新档案或更新本年度实时档案。
    if not year_record_exists or year == TODAY.year:
        write_page(f"{year} 年总打卡热力图（历史档案）", make_year(year), f"{year_dir}/index.html")
    set_archive_record(record_map, f"{year}年总热力图", "年度", year, None,
                       {"总热力图": f"{BASE_URL}/{year_dir}/"})
    months = {date.fromisoformat(d).month for d in daily if date.fromisoformat(d).year == year}
    if year == TODAY.year:
        months.add(TODAY.month)
    for month in sorted(months):
        month_record_exists = ("月度", year, month) in record_map
        is_current_month = year == TODAY.year and month == TODAY.month
        urls = {}
        for category in CATEGORIES:
            path = f"archive/{year}/{month:02d}/{CATEGORY_PATHS[category]}/index.html"
            # 已存在的往年月份只保留原页面；当前月可持续更新，月末后冻结。
            if not month_record_exists or is_current_month:
                write_page(f"{category} · {year}年{month}月（历史档案）", make_month(year, month, category), path)
            urls[{"书籍":"书籍热力图", "影视":"影视热力图", "游戏":"游戏热力图", "做饭":"做饭热力图", "厨具":"厨具热力图"}[category]] = f"{BASE_URL}/{path}"
        set_archive_record(record_map, f"{year}年{month}月热力图", "月度", year, month, urls)

print(f"历史热力图归档完成：处理 {len(years)} 个年份的数据。")
