# gs_sign_calendar

一个基于 [早柚核心 (gsuid_core)](https://github.com/Genshin-bots/gsuid_core) 的动态签到日历插件，支持盲盒开图、自定义背景和图片池管理。

## 功能

- 每日签到，生成精美日历卡片
- 盲盒机制：签到时随机开出图片，同月内不重复
- 自定义背景图（`sign-bj` 目录）
- 自定义盲盒图片池（`sign_images` 目录）
- 主人管理命令

## 功能展示

下面是签到日历渲染效果示例：

![签到日历演示](docs/sign-calendar-demo.png)

> 请将截图保存为 `gs_sign_calendar/docs/sign-calendar-demo.png`，文档将自动展示该效果图。

## 指令列表

| 指令 | 说明 | 权限 |
|------|------|------|
| `🦌` | 签到（已签到则展示日历） | 所有人 |
| `🦌日历` / `签到日历` / `/签到日历` | 查看本月签到日历 | 所有人 |
| `🦌满` | 一键签满本月 | 主人 |
| `🦌重置` | 重置本月所有人签到记录 | 主人 |
| `🦌删图 <关键词>` | 删除图片池中文件名匹配的图片 | 主人 |
| `🦌图池` | 查看图片池数量 | 所有人 |

## 安装

1. 将本插件目录放入 `gsuid_core/plugins/` 下
2. 确保已安装依赖：`Pillow`、`Jinja2`、`playwright`（用于渲染日历图片）
3. 如果 Playwright 浏览器未安装，执行：
   ```bash
   playwright install chromium
   ```
4. 重启 bot 即可

## 目录结构

```
gs_sign_calendar/
├── __init__.py          # 主逻辑
├── upload.py            # 图片管理模块
├── templates/
│   └── calendar.html    # 日历渲染模板
├── sign_images/         # 盲盒图片池（放入 png/jpg/gif/webp）
├── sign-bj/             # 背景图（随机选取）
├── sign_state.json      # 签到数据（自动生成）
└── README.md
```

## 自定义

### 背景图

将图片放入 `sign-bj/` 目录，支持 png、jpg、webp 格式。每次渲染会随机选取一张作为日历背景。

### 盲盒图片池

将图片放入 `sign_images/` 目录。签到时会从池中随机分配图片，同一用户同月内每天不重复（图片数量充足时）。

## 开源协议

本项目基于 [GNU General Public License v3.0 (GPLv3)](https://www.gnu.org/licenses/gpl-3.0.html) 开源。

## 致谢

感谢 [猫砸 (MeowAndy)](https://github.com/MeowAndy) 提供的 AI 技术支持，为本项目的开发与迭代做出了重要贡献。