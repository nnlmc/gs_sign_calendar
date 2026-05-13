from __future__ import annotations

import json
import base64
import random
import hashlib
import calendar
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from gsuid_core.bot import Bot
from gsuid_core.config import core_config
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import Plugins, SV

from . import upload  # noqa: F401 - 加载上传切图模块

try:
    from playwright.async_api import async_playwright
except Exception:
    async_playwright = None

try:
    from XutheringWavesUID.XutheringWavesUID.utils.render_utils import (
        render_html as xwuid_render_html,
    )
except Exception:
    xwuid_render_html = None


Plugins(
    name='gs_sign_calendar',
    allow_empty_prefix=True,
)

sv = SV('签到日历')
BASE_DIR = Path(__file__).parent
TEMPLATE_ROOT = BASE_DIR / 'templates'
STATE_PATH = BASE_DIR / 'sign_state.json'
SIGN_IMAGES_DIR = BASE_DIR / 'sign_images'
BG_IMAGES_DIR = BASE_DIR / 'sign-bj'

sign_templates = Environment(
    loader=FileSystemLoader([str(TEMPLATE_ROOT)]),
    autoescape=select_autoescape(('html', 'xml')),
)

QQ_AVATAR_URL = 'http://q1.qlogo.cn/g?b=qq&nk={qid}&s=640'

# 盲盒 SVG - 圆润可爱盲盒风格
MYSTERY_BOX_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <defs>
    <linearGradient id="boxBody" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#b8e6ff"/>
      <stop offset="100%" style="stop-color:#7ec8e3"/>
    </linearGradient>
    <linearGradient id="boxLid" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#ffe066"/>
      <stop offset="100%" style="stop-color:#ffb347"/>
    </linearGradient>
    <linearGradient id="star" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#fff176"/>
      <stop offset="100%" style="stop-color:#ffee58"/>
    </linearGradient>
    <filter id="ds">
      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000" flood-opacity="0.12"/>
    </filter>
  </defs>
  <rect x="0" y="0" width="200" height="200" rx="20" fill="#f5f0ff"/>
  <rect x="40" y="80" width="120" height="90" rx="18" fill="url(#boxBody)" filter="url(#ds)"/>
  <rect x="40" y="80" width="120" height="90" rx="18" fill="none" stroke="#fff" stroke-width="2" opacity="0.5"/>
  <ellipse cx="100" cy="170" rx="50" ry="6" fill="#000" opacity="0.06"/>
  <rect x="34" y="66" width="132" height="24" rx="12" fill="url(#boxLid)" filter="url(#ds)"/>
  <rect x="34" y="66" width="132" height="24" rx="12" fill="none" stroke="#fff" stroke-width="1.5" opacity="0.6"/>
  <rect x="90" y="66" width="20" height="104" rx="6" fill="#fff" opacity="0.2"/>
  <rect x="40" y="90" width="120" height="6" rx="3" fill="#fff" opacity="0.2"/>
  <circle cx="100" cy="52" r="16" fill="url(#boxLid)" filter="url(#ds)"/>
  <path d="M86 52 C86 38 100 32 100 46" fill="none" stroke="#ff9800" stroke-width="4" stroke-linecap="round"/>
  <path d="M114 52 C114 38 100 32 100 46" fill="none" stroke="#ff9800" stroke-width="4" stroke-linecap="round"/>
  <text x="100" y="140" text-anchor="middle" font-size="40" font-weight="900" fill="#fff" font-family="Arial" opacity="0.85">?</text>
  <polygon points="155,45 158,51 165,52 160,57 161,64 155,60 149,64 150,57 145,52 152,51" fill="url(#star)" opacity="0.9"/>
  <polygon points="50,100 52,104 56,105 53,108 54,112 50,110 46,112 47,108 44,105 48,104" fill="url(#star)" opacity="0.7"/>
  <polygon points="160,100 161,103 164,103 162,105 163,108 160,107 157,108 158,105 156,103 159,103" fill="url(#star)" opacity="0.6"/>
  <circle cx="60" cy="75" r="3" fill="#fff" opacity="0.6"/>
  <circle cx="145" cy="130" r="2.5" fill="#fff" opacity="0.5"/>
  <circle cx="70" cy="150" r="2" fill="#fff" opacity="0.4"/>
</svg>'''


def _get_mystery_box_data_uri() -> str:
    b64 = base64.b64encode(MYSTERY_BOX_SVG.encode('utf-8')).decode('ascii')
    return f'data:image/svg+xml;base64,{b64}'


def _get_bg_image_data_uri() -> str:
    """从 sign-bj 目录随机选一张背景图，转为 base64 data URI"""
    if not BG_IMAGES_DIR.exists():
        return ''
    bgs = [
        f for f in BG_IMAGES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')
    ]
    if not bgs:
        return ''
    chosen = random.choice(bgs)
    try:
        data = chosen.read_bytes()
        b64 = base64.b64encode(data).decode('ascii')
        suffix = chosen.suffix.lower()
        mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}.get(suffix, 'image/jpeg')
        return f'data:{mime};base64,{b64}'
    except Exception:
        return ''


def _scan_sign_images() -> List[Path]:
    """扫描所有可用的签到盲盒图片"""
    images = []
    if not SIGN_IMAGES_DIR.exists():
        return images
    for f in SIGN_IMAGES_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
            images.append(f)
        elif f.is_dir():
            for sf in f.iterdir():
                if sf.is_file() and sf.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
                    images.append(sf)
    return sorted(images, key=lambda p: p.name)


def _get_image_for_day(user_id: str, year: int, month: int, day: int, images: List[Path], shuffle_seed: int = 0) -> str:
    """根据 user_id + 年月 + shuffle_seed 生成一个不重复的排列，每天对应不同图片"""
    if not images:
        return _get_mystery_box_data_uri()
    seed_str = f'{user_id}-{year}-{month}-{shuffle_seed}'
    rng = random.Random(seed_str)
    shuffled = list(range(len(images)))
    rng.shuffle(shuffled)
    idx = shuffled[(day - 1) % len(shuffled)]
    img_path = images[idx]
    try:
        data = img_path.read_bytes()
        b64 = base64.b64encode(data).decode('ascii')
        suffix = img_path.suffix.lower()
        mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}.get(suffix, 'image/png')
        return f'data:{mime};base64,{b64}'
    except Exception:
        return _get_mystery_box_data_uri()


def _load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    except Exception as e:
        logger.warning(f'[gs_sign_calendar] 读取签到状态失败: {e}')
        return {}


def _save_state(state: Dict[str, Any]) -> None:
    temp = STATE_PATH.with_suffix('.json.tmp')
    try:
        temp.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        temp.replace(STATE_PATH)
    except Exception as e:
        logger.warning(f'[gs_sign_calendar] 保存签到状态失败: {e}')
        try:
            if temp.exists():
                temp.unlink()
        except Exception:
            pass


def _get_user_key(ev: Event) -> str:
    return f'{ev.user_id}'


def _get_month_key() -> str:
    now = datetime.now()
    return f'{now.year}-{now.month:02d}'


def _get_today_day() -> int:
    return datetime.now().day


def _get_user_signs(state: Dict[str, Any], user_key: str, month_key: str) -> list:
    return state.get(user_key, {}).get(month_key, [])


def _do_sign(state: Dict[str, Any], user_key: str, month_key: str, day: int) -> None:
    """执行签到（仅添加，不 toggle）"""
    user_data = state.setdefault(user_key, {})
    signs = user_data.setdefault(month_key, [])
    if day not in signs:
        signs.append(day)
        signs.sort()


def _build_calendar_context(ev: Event, state: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now()
    year = now.year
    month = now.month
    month_key = _get_month_key()
    user_key = _get_user_key(ev)
    signed_days = _get_user_signs(state, user_key, month_key)

    days_in_month = calendar.monthrange(year, month)[1]
    first_weekday = calendar.monthrange(year, month)[0]
    # 周一为第一列，first_weekday 已经是 0=周一，直接用
    first_day_offset = first_weekday

    avatar_url = QQ_AVATAR_URL.format(qid=ev.user_id)
    mystery_box = _get_mystery_box_data_uri()
    images = _scan_sign_images()
    shuffle_seed = state.get('_shuffle_seed', 0)

    cells = []
    for _ in range(first_day_offset):
        cells.append({'day': 0, 'signed': False, 'img': ''})
    for day in range(1, days_in_month + 1):
        if day in signed_days:
            img = _get_image_for_day(user_key, year, month, day, images, shuffle_seed)
            cells.append({'day': day, 'signed': True, 'img': img})
        else:
            cells.append({'day': day, 'signed': False, 'img': mystery_box})

    title = f'{year}-{month:02d} 签到日历'
    bg_image = _get_bg_image_data_uri()

    return {
        'title': title,
        'avatar_url': avatar_url,
        'bg_image': bg_image,
        'cells': cells,
        'year': year,
        'month': month,
        'days_in_month': days_in_month,
        'signed_count': len(signed_days),
    }


async def _render_calendar(context: Dict[str, Any]) -> Optional[bytes]:
    if xwuid_render_html is not None:
        try:
            return await xwuid_render_html(sign_templates, 'calendar.html', context)
        except Exception as e:
            logger.warning(f'[gs_sign_calendar] 外置渲染失败，回退本地: {e}')

    if async_playwright is None:
        return None

    template = sign_templates.get_template('calendar.html')
    html_content = template.render(**context)

    playwright = None
    browser = None
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page(viewport={'width': 820, 'height': 1044})
        await page.set_content(html_content, wait_until='load')
        container = page.locator('.container')
        await page.wait_for_selector('.container', timeout=3000)
        size = await container.evaluate(
            """(el) => {
                const rect = el.getBoundingClientRect();
                return { width: Math.ceil(rect.width), height: Math.ceil(rect.height) };
            }"""
        )
        if size and size.get('width') and size.get('height'):
            await page.set_viewport_size({
                'width': max(1, int(size['width'])),
                'height': max(1, int(size['height'])),
            })
        return await container.screenshot(type='jpeg', quality=90)
    finally:
        if browser is not None:
            await browser.close()
        if playwright is not None:
            await playwright.stop()


def _is_master(ev: Event) -> bool:
    masters = core_config.get_config('masters') or []
    return str(ev.user_id) in {str(m) for m in masters}


@sv.on_command('🦌满', block=True)
async def handle_sign_full(bot: Bot, ev: Event):
    if not _is_master(ev):
        await bot.send('只有 bot 主人可以使用此命令')
        return

    state = _load_state()
    user_key = _get_user_key(ev)
    month_key = _get_month_key()
    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]

    user_data = state.setdefault(user_key, {})
    user_data[month_key] = list(range(1, days_in_month + 1))
    _save_state(state)

    context = _build_calendar_context(ev, state)
    image = await _render_calendar(context)
    if image:
        await bot.send(image)
    else:
        await bot.send(f'已一键签满本月全部 {days_in_month} 天')


@sv.on_command('🦌重置', block=True)
async def handle_reset(bot: Bot, ev: Event):
    if not _is_master(ev):
        await bot.send('只有 bot 主人可以使用此命令')
        return

    state = _load_state()
    month_key = _get_month_key()

    # 清除所有用户本月签到记录
    count = 0
    for user_key in list(state.keys()):
        if user_key.startswith('_'):
            continue
        if isinstance(state[user_key], dict) and month_key in state[user_key]:
            del state[user_key][month_key]
            count += 1

    # 递增 shuffle_seed，让图片排列重新洗牌
    state['_shuffle_seed'] = state.get('_shuffle_seed', 0) + 1

    _save_state(state)
    await bot.send(f'已重置本月签到记录，清除了 {count} 位用户的数据')


@sv.on_command('🦌', block=True)
@sv.on_command('鹿', block=True)
async def handle_sign(bot: Bot, ev: Event):
    state = _load_state()
    user_key = _get_user_key(ev)
    month_key = _get_month_key()
    today = _get_today_day()

    signed_days = _get_user_signs(state, user_key, month_key)
    if today in signed_days:
        context = _build_calendar_context(ev, state)
        image = await _render_calendar(context)
        if image:
            await bot.send(image)
        else:
            await bot.send(f'今天已经签到过了！本月已签到 {len(signed_days)} 天')
        return

    _do_sign(state, user_key, month_key, today)
    _save_state(state)

    context = _build_calendar_context(ev, state)
    image = await _render_calendar(context)
    if image:
        await bot.send(image)
    else:
        signed_days = _get_user_signs(state, user_key, month_key)
        await bot.send(f'签到成功！本月已签到 {len(signed_days)} 天')


@sv.on_command('/签到日历', block=True)
@sv.on_command('签到日历', block=True)
@sv.on_command('🦌日历', block=True)
async def handle_calendar(bot: Bot, ev: Event):
    state = _load_state()
    context = _build_calendar_context(ev, state)
    image = await _render_calendar(context)
    if image:
        await bot.send(image)
    else:
        user_key = _get_user_key(ev)
        month_key = _get_month_key()
        signed_days = _get_user_signs(state, user_key, month_key)
        now = datetime.now()
        await bot.send(
            f'{now.year}-{now.month:02d} 签到日历\n'
            f'已签到: {", ".join(str(d) for d in signed_days) if signed_days else "无"}\n'
            f'本月共签到 {len(signed_days)} 天'
        )