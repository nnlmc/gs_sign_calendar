from __future__ import annotations

import base64
import random
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

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

sv_help = SV('签到帮助')
HELP_DIR = Path(__file__).parent
HELP_TEMPLATE_DIR = HELP_DIR / 'templates'
BG_DIR = HELP_DIR.parent / 'sign-bj'

help_templates = Environment(
    loader=FileSystemLoader([str(HELP_TEMPLATE_DIR)]),
    autoescape=select_autoescape(('html', 'xml')),
)


def _get_bg_data_uri() -> str:
    if not BG_DIR.exists():
        return ''
    bgs = [
        f for f in BG_DIR.iterdir()
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


async def _render_help() -> Optional[bytes]:
    context = {
        'bg_image': _get_bg_data_uri(),
    }

    if xwuid_render_html is not None:
        try:
            return await xwuid_render_html(help_templates, 'help.html', context)
        except Exception as e:
            logger.warning(f'[gs_sign_calendar] help 外置渲染失败，回退本地: {e}')

    if async_playwright is None:
        return None

    template = help_templates.get_template('help.html')
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


@sv_help.on_command('🦌帮助', block=True)
@sv_help.on_command('鹿帮助', block=True)
async def handle_help(bot: Bot, ev: Event):
    image = await _render_help()
    if image:
        await bot.send(image)
    else:
        await bot.send(
            '🦌 签到日历 帮助\n'
            '━━━━━━━━━━━━━━━\n'
            '🦌 — 每日签到，开盲盒\n'
            '🦌日历 / 签到日历 — 查看本月签到日历\n'
            '🦌帮助 / 鹿帮助 — 显示本帮助\n'
            '━━━━━━━━━━━━━━━\n'
            '主人命令:\n'
            '🦌满 — 一键签满本月\n'
            '🦌重置 — 重置本期所有签到记录'
        )