"""签到日历 - 图片管理模块"""
from __future__ import annotations

from pathlib import Path

from gsuid_core.bot import Bot
from gsuid_core.config import core_config
from gsuid_core.models import Event
from gsuid_core.sv import SV

BASE_DIR = Path(__file__).parent
SIGN_IMAGES_DIR = BASE_DIR / 'sign_images'

sv_upload = SV('签到图片管理')


def _is_master(ev: Event) -> bool:
    masters = core_config.get_config('masters') or []
    return str(ev.user_id) in {str(m) for m in masters}


def _count_pool_images() -> int:
    if not SIGN_IMAGES_DIR.exists():
        return 0
    count = 0
    for f in SIGN_IMAGES_DIR.rglob('*'):
        if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
            count += 1
    return count


@sv_upload.on_command('🦌删图', block=True)
async def handle_delete_images(bot: Bot, ev: Event):
    if not _is_master(ev):
        await bot.send('只有 bot 主人可以删除图片')
        return

    text = (getattr(ev, 'text', '') or '').strip()
    keyword = text.replace('🦌删图', '').strip()

    if not keyword:
        await bot.send('请指定要删除的图片关键词，格式: 🦌删图 <文件名关键词>\n发送 🦌图池 查看当前图片列表')
        return

    if not SIGN_IMAGES_DIR.exists():
        await bot.send('图片池为空')
        return

    deleted = 0
    for f in SIGN_IMAGES_DIR.rglob('*'):
        if f.is_file() and keyword in f.stem and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
            f.unlink()
            deleted += 1

    total = _count_pool_images()
    await bot.send(f'已删除 {deleted} 张包含「{keyword}」的图片\n当前池中共 {total} 张图')


@sv_upload.on_command('🦌图池', block=True)
async def handle_pool_info(bot: Bot, ev: Event):
    total = _count_pool_images()
    await bot.send(f'当前盲盒图片池共 {total} 张图片')