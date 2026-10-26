import os
import html
from pathlib import Path
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from calendar import monthrange
from notion_client import Client
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
import requests
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
CATEGORY_COLORS = {
    "书籍": ["#FFFFFF", "#E2F5E8", "#BFE8CD", "#91D6A8", "#65C681", "#3EAD61", "#268A48", "#176B36", "#0B4825"],
    "影视": ["#FFFFFF", "#F0E5FF", "#DCC5FF", "#C5A0FF", "#AA7BFA", "#8B55E8", "#7038C8", "#54259F", "#35166B"],
    "游戏": ["#FFFFFF", "#E0F0FF", "#B9DEFF", "#8BC5FF", "#5BA8F5", "#3488E0", "#2169BF", "#174D96", "#103366"],
    "做饭": ["#FFFFFF", "#FFF9D9", "#FFF0A3", "#FFE16B", "#FFCF3F", "#F5B51B", "#E99A0C", "#CF7508", "#A84E08"],
    "厨具": ["#FFFFFF", "#FFE8F0", "#FFC9DD", "#FFA4C8", "#F77EAF", "#E85C98", "#D43D80", "#B52667", "#8C174D"]
}
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
.panel{width:fit-content;background:white;border:1px solid #d8dee4;border-radius:12px;padding:16px;margin:0}
.scroll{width:max-content;overflow:visible;padding:2px 2px 8px}
.month-labels{display:grid;height:30px;align-items:start;font-size:11px;line-height:16px;color:#57606a;column-gap:3px}
.heatmap{display:grid;grid-template-rows:repeat(7,13px);grid-auto-flow:column;gap:3px;width:max-content}
.cell{width:13px;height:13px;border-radius:3px;border:1px solid rgba(27,31,36,.06)}.outside{background:transparent;border-color:transparent}
.legend{display:flex;align-items:center;gap:4px;color:#57606a;font-size:11px;margin:14px 0 0}.legend-cell{display:inline-block;width:12px;height:12px;border-radius:3px}
.weekday-row,.month-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px}.weekday-row{margin-bottom:7px;color:#57606a;font-size:12px;text-align:center}
.month-day{position:relative;aspect-ratio:1;min-width:0;border-radius:5px;border:1px solid rgba(27,31,36,.06);display:flex;align-items:center;justify-content:center}
.day-number{font-size:11px;color:#24292f;opacity:.85}.month-summary{font-size:12px;color:#57606a;margin:12px 0 0}footer{color:#57606a;font-size:12px;margin-top:18px}
"""

def write_heatmap_png(year, month, category, filename):
    """生成与实时网页布局接近的历史热力图 PNG。"""
    cell = 13
    gap = 3
    margin = 24
    label_width = 38
    top_height = 48

    if month is None:
        first = date(year, 1, 1)
        last = date(year, 12, 31)
        title = f"{year} 年总打卡热力图"
        heading = f"{year} 年总打卡 · 全年"
    else:
        first = date(year, month, 1)
        last = date(year, month, monthrange(year, month)[1])
        title = f"{category}打卡热力图"
        heading = f"{category} · {year}年{month}月"

    # 年度图按周日开列，和网页年度图保持相近的排列。
    if month is None:
        start = first - timedelta(days=(first.weekday() + 1) % 7)
        end = last + timedelta(days=(5 - last.weekday()) % 7)
        week_start_sunday = True
    else:
        start = first - timedelta(days=first.weekday())
        end = last + timedelta(days=6 - last.weekday())
        week_start_sunday = False

    weeks = ((end - start).days + 1) // 7
    width = margin * 2 + label_width + weeks * (cell + gap)
    height = margin * 2 + top_height + 7 * (cell + gap) + 44

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin, margin), title, fill="#242424")
    draw.text((margin, margin + 23), heading, fill="#555555")

    # 月份标签。
    if month is None:
        for m in range(1, 13):
            md = date(year, m, 1)
            col = (md - start).days // 7
            x = margin + label_width + col * (cell + gap)
            draw.text((x, margin + top_height), f"{m}月", fill="#555555")
    else:
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        for i, label in enumerate(weekdays):
            y = margin + top_height + i * (cell + gap)
            draw.text((margin, y), label, fill="#555555")

    grid_top = margin + top_height + (0 if month is None else 0)

    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        if not first <= day <= last:
            continue

        counts = daily.get(day.isoformat(), {})
        count = counts.get("总计", 0) if month is None else counts.get(category, 0)
        colors = TOTAL_COLORS if month is None else CATEGORY_COLORS[category]
        color = colors[min(count, len(colors) - 1)]

        if week_start_sunday:
            col = (day - start).days // 7
            row = (day.weekday() + 1) % 7
        else:
            col = (day - start).days // 7
            row = day.weekday()

        x = margin + label_width + col * (cell + gap)
        y = grid_top + row * (cell + gap)
        draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=color)

    # 颜色图例：年度总图和分类月图分别使用对应配色。
    legend_y = grid_top + 7 * (cell + gap) + 8
    draw.text((margin, legend_y), "少", fill="#555555")
    legend_x = margin + 24

    colors = TOTAL_COLORS if month is None else CATEGORY_COLORS[category]

    for color in colors:
        draw.rectangle(
            (legend_x, legend_y, legend_x + cell - 1, legend_y + cell - 1),
            fill=color
        )
        legend_x += cell + 3

    draw.text((legend_x + 2, legend_y), "多", fill="#555555")

    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")




def screenshot_html(html_file, png_file, is_monthly=False):
    """按年度/月度布局截取热力图及指定的统计内容。"""
    html_path = Path(html_file).resolve()
    png_path = Path(png_file)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1600, "height": 1200},
            device_scale_factor=2,
        )
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready")

        dimensions = page.evaluate("""(isMonthly) => {
            const title = document.querySelector('body > h1');
            const summary = document.querySelector('body > .summary');
            const panel = document.querySelector('body > section.panel');
            const footer = document.querySelector('body > footer');

            if (!panel) {
                return {
                    width: document.documentElement.scrollWidth,
                    height: document.documentElement.scrollHeight
                };
            }

            const panelRect = panel.getBoundingClientRect();
            const titleRect = title?.getBoundingClientRect();
            const summaryRect = summary?.getBoundingClientRect();

            // 年度图需要标题、说明、全年热力图和图例。
            // 月度图需要标题、说明、日历热力图和底部统计。
            const targets = [
                panel,
                title,
                summary,
                panel.querySelector('.scroll'),
                panel.querySelector('.heatmap'),
                panel.querySelector('.month-grid'),
                panel.querySelector('.legend'),
                panel.querySelector('.month-summary'),
                panel.querySelector('.weekday-row')
            ].filter(Boolean);

            const rects = targets.map(el => el.getBoundingClientRect());

            const right = Math.max(...rects.map(r => r.right));
            const bottom = Math.max(...rects.map(r => r.bottom));

            // 年度图的横向内容以热力图和图例为准；
            // 月度图的横向内容以日历面板为准。
            return {
                width: Math.ceil(right + 24),
                height: Math.ceil(bottom + 24)
            };
        }""", is_monthly)

        page.set_viewport_size({
            "width": max(dimensions["width"], 800),
            "height": max(dimensions["height"], 300),
        })

        # 等待视口调整后重新计算布局，再按完整页面截图。
        page.evaluate("document.fonts.ready")
        page.screenshot(
            path=str(png_path),
            full_page=True,
        )
        browser.close()



def upload_png_to_notion(image_path):
    """将 PNG 图片上传到 Notion，返回上传文件 ID。"""
    token = os.environ["NOTION_TOKEN"]
    path = Path(image_path)

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2026-03-11",
    }

    # 第一步：创建文件上传任务
    response = requests.post(
        "https://api.notion.com/v1/file_uploads",
        headers=headers,
        json={
            "filename": path.name,
            "content_type": "image/png",
        },
        timeout=60,
    )
    response.raise_for_status()
    upload_id = response.json()["id"]

    # 第二步：上传图片内容
    with path.open("rb") as image_file:
        response = requests.post(
            f"https://api.notion.com/v1/file_uploads/{upload_id}/send",
            headers=headers,
            files={
                "file": (path.name, image_file, "image/png"),
            },
            timeout=120,
        )
    response.raise_for_status()

    print(f"PNG uploaded to Notion: {path.name}")
    return upload_id

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
        cells.append(f'<span class="cell" style="background:{TOTAL_COLORS[min(count, len(TOTAL_COLORS)-1)]}" title="{tip}"></span>')
    labels = []
    for m in range(1, 13):
        md = date(year, m, 1)
        col = (md - start).days // 7 + 1
        labels.append(f'<span style="grid-column:{col}">{m}月</span>')
    legend = ''.join(
    f'<span class="legend-cell" style="background:{TOTAL_COLORS[i]}"></span>'
    for i in range(len(TOTAL_COLORS))
    )
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
        colors = CATEGORY_COLORS[category]
        cells.append(f'<span class="month-day" style="background:{colors[min(count, len(colors)-1)]}" title="{tip}"><span class="day-number">{n}</span></span>')
    while len(cells) % 7:
        cells.append('<span class="cell outside"></span>')
    section = f'<section class="panel"><h2>{html.escape(category)} · {year}年{month}月</h2><div class="weekday-row"><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span></div><div class="month-grid">{"".join(cells)}</div><p class="month-summary">本月打卡：{total} 次</p></section>'
    return f'<h1>{html.escape(category)}打卡热力图</h1><div class="summary">{year}年{month}月历史记录；悬停方格可查看当天详情。</div>{section}'


def get_archive_records():
    records = []
    archive_data_source_id = get_archive_data_source_id()
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

def set_archive_record(record_map, title, kind, year, month, urls, preview_file=None):
    # 历史月份和往年只创建一次；当前月份/当前年度允许随日常打卡更新。
    key = (kind, year, month)
    existing = record_map.get(key)

    is_current = (
        (kind == "年度" and year == TODAY.year)
        or (
            kind.endswith("月度")
            and year == TODAY.year
            and month == TODAY.month
        )
    )

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
        page_id = existing["id"]
        notion.pages.update(page_id=page_id, properties=properties)
    else:
        created = notion.pages.create(
            parent={"data_source_id": get_archive_data_source_id()},
            properties=properties,
        )
        page_id = created["id"]

    if preview_file:
        upload_id = upload_png_to_notion(preview_file)

        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
                "Notion-Version": "2026-03-11",
                "Content-Type": "application/json",
            },
            json={
                "properties": {
                    "热力图预览": {
                        "files": [
                            {
                                "type": "file_upload",
                                "file_upload": {"id": upload_id},
                                "name": Path(preview_file).name,
                            }
                        ]
                    }
                }
            },
            timeout=60,
        )
        response.raise_for_status()
        print(f"Heatmap preview attached: {preview_file}")
record_map = {}
for rec in get_archive_records():
    kind = prop_value(rec, "档案类型")
    year = prop_value(rec, "年份")
    month = prop_value(rec, "月份")
    if kind and year is not None:
        record_map[
            (kind, int(year), int(month) if month is not None else None)
        ] = rec

# 每个分类对应独立的月度档案类型和 URL 属性。
MONTHLY_TYPES = {
    "书籍": "书籍月度",
    "影视": "影视月度",
    "游戏": "游戏月度",
    "做饭": "做饭月度",
    "厨具": "厨具月度",
}

URL_PROPERTIES = {
    "书籍": "书籍热力图",
    "影视": "影视热力图",
    "游戏": "游戏热力图",
    "做饭": "做饭热力图",
    "厨具": "厨具热力图",
}

# 收集有数据的年份，并确保当前年份也会生成。
years = {date.fromisoformat(d).year for d in daily}
years.add(TODAY.year)

for year in sorted(years):
    year_dir = f"archive/{year}"
    year_record_exists = ("年度", year, None) in record_map

    # 年度档案逻辑保持不变。
    if True:
        write_page(
            f"{year} 年总打卡热力图（历史档案）",
            make_year(year),
            f"{year_dir}/index.html",
        )
        screenshot_html(
            f"{year_dir}/index.html",
            f"{year_dir}/heatmap.png",
        )

    set_archive_record(
        record_map,
        f"{year}年总热力图",
        "年度",
        year,
        None,
        {"总热力图": f"{BASE_URL}/{year_dir}/"},
        preview_file=(
            f"{year_dir}/heatmap.png"
            if year == TODAY.year
            else None
        ),
    )

    # 找出该年份有打卡数据的月份。
    months = {
        date.fromisoformat(d).month
        for d in daily
        if date.fromisoformat(d).year == year
    }

    if year == TODAY.year:
        months.add(TODAY.month)

    for month in sorted(months):
        is_current_month = (
            year == TODAY.year and month == TODAY.month
        )

        for category in CATEGORIES:
            kind = MONTHLY_TYPES[category]
            key = (kind, year, month)
            record_exists = key in record_map

            # 历史月份已有档案时不重复生成；
            # 当月档案每次运行都更新。
            if False:
                continue

            category_dir = (
                f"archive/{year}/{month:02d}/"
                f"{CATEGORY_PATHS[category]}"
            )
            html_path = f"{category_dir}/index.html"
            png_path = f"{category_dir}/heatmap.png"

            write_page(
                f"{category} · {year}年{month}月（历史档案）",
                make_month(year, month, category),
                html_path,
            )

            # 使用月度截图参数生成 PNG 预览。
            screenshot_html(html_path, png_path, is_monthly=True)

            set_archive_record(
                record_map,
                f"{year}年{month}月{category}热力图",
                kind,
                year,
                month,
                {
                    URL_PROPERTIES[category]:
                        f"{BASE_URL}/{html_path}"
                },
                preview_file=png_path,
            )

print(f"历史热力图归档完成：处理 {len(years)} 个年份的数据。")
