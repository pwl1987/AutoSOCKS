"""TUI L3 全屏交互界面 - curses 主界面

功能：
- 双栏布局：左侧菜单 + 右侧实时状态面板
- 分组菜单（代理管理 / 代理工具 / 配置编辑 / Profile / 系统工具 / 退出）
- 右侧面板实时显示：服务状态、配置信息、延迟、出口 IP
- 后台运行：代理通过 systemd 独立运行，TUI 关闭不影响代理
- 所有配置项均可通过 TUI 内置对话框编辑（不离开 TUI）
- 消息超时自动清除
- 快捷键操作
- 自适应终端大小
"""
from __future__ import annotations

import curses
import os
import re
import shutil
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from autosocks import __version__
from autosocks.core.config import load_config, save_config
from autosocks.core.service import service_start, service_stop, service_restart, service_is_active


CONFIG_PATH = Path("/etc/autosocks/config.conf")
PROFILE_DIR = Path("/etc/autosocks/profiles")
_REFRESH_INTERVAL = 2.0
_MSG_TIMEOUT = 5.0
_LATENCY_INTERVAL = 10.0
_SCROLL_SPEED = 2

# ── 颜色对 ID ──
# 色彩体系设计原则：
#  - 使用终端原生 8 色 + 属性（bold/dim）构建层次丰富的配色
#  - 主色调：青色系（科技感），辅助色：绿/黄/红（状态指示）
#  - 减少直接使用饱和色，多用 dim + bold 制造层次
_CLR_TITLE = 1        # 标题栏：亮青粗体
_CLR_RUNNING = 2      # 运行中：绿色
_CLR_STOPPED = 3      # 已停止：红色
_CLR_SELECTED = 4     # 选中项：黑底青字（高对比反色）
_CLR_GROUP = 5        # 分组标题：亮黄粗体
_CLR_MSG = 6          # 消息正文：白色
_CLR_KEYBAR = 7       # 底部键栏：黑底白字
_CLR_BORDER = 8       # 边框/分隔线：蓝色
_CLR_DIM = 9          # 次要文本：暗白（配合 A_DIM）
_CLR_SUCCESS = 10     # 成功消息：绿色粗体
_CLR_ERROR = 11       # 错误消息：红色粗体
_CLR_HINT = 12        # 操作提示：暗青色
_CLR_WARN = 13        # 警告：黄色
_CLR_ACCENT = 14      # 强调标签：品红色
_CLR_VALUE = 15       # 数据值：亮白色粗体
_CLR_DLG_BORDER = 16  # 对话框边框：青色
_CLR_DLG_TITLE = 17   # 对话框标题：亮黄粗体
_CLR_DLG_INPUT = 18   # 输入框：白底蓝字
_CLR_MENU_DIM = 19    # 菜单未选中项：暗白色


@dataclass
class MenuItem:
    """菜单项"""
    label: str
    action: str
    group: str = ""
    shortcut: str = ""


@dataclass
class LatencyInfo:
    """延迟信息"""
    ms: float = -1.0
    exit_ip: str | None = None
    timestamp: float = 0.0


class TUIApp:
    """curses 全屏 TUI 应用"""

    def __init__(self) -> None:
        self.items = self.default_menu_items()
        self.selected = 0
        self.running = True
        self.message = ""
        self.message_time = 0.0
        self._config_cache: dict[str, object] = {}
        self._config_cache_time = 0.0
        self._active_cache = False
        self._active_cache_time = 0.0
        self._latency = LatencyInfo()
        self._scroll_offset = 0
        self._menu_width = 32
        self._last_draw = 0.0
        self._dirty = True
        self._last_latency_ts = 0.0
        self._stdscr: curses.window | None = None

    # ── 菜单定义 ──

    @staticmethod
    def default_menu_items() -> list[MenuItem]:
        return [
            MenuItem("── 代理管理 ──", "", group="header"),
            MenuItem("  启动代理", "start", shortcut="s"),
            MenuItem("  停止代理", "stop", shortcut="S"),
            MenuItem("  重启代理", "restart", shortcut="r"),
            MenuItem("  运行状态", "status", shortcut="i"),
            MenuItem("  健康检查", "health", shortcut="h"),
            MenuItem("  延迟测试", "latency_test"),
            MenuItem("── 代理工具 ──", "", group="header"),
            MenuItem("  HTTP 代理转发", "http_proxy"),
            MenuItem("  环境变量", "env"),
            MenuItem("  Shell 集成", "shell_integration"),
            MenuItem("── 配置编辑 ──", "", group="header"),
            MenuItem("  配置向导", "install"),
            MenuItem("  快速上手", "setup_wizard"),
            MenuItem("  服务器设置", "edit_server"),
            MenuItem("  本地端口设置", "edit_local"),
            MenuItem("  认证设置", "edit_auth"),
            MenuItem("  SSH 参数", "edit_ssh"),
            MenuItem("  重连设置", "edit_reconnect"),
            MenuItem("  日志设置", "edit_log"),
            MenuItem("  Webhook 告警", "edit_webhook"),
            MenuItem("  GeoIP 分流", "edit_geo"),
            MenuItem("── Profile ──", "", group="header"),
            MenuItem("  查看 Profiles", "profile_list"),
            MenuItem("  创建 Profile", "profile_create"),
            MenuItem("  切换 Profile", "profile_switch"),
            MenuItem("  删除 Profile", "profile_delete"),
            MenuItem("── 系统工具 ──", "", group="header"),
            MenuItem("  查看完整配置", "view_config"),
            MenuItem("  查看日志", "view_log"),
            MenuItem("  检查更新", "update"),
            MenuItem("  后台运行", "daemon", shortcut="d"),
            MenuItem("── 退出 ──", "", group="header"),
            MenuItem("  退出 TUI", "quit", shortcut="q"),
        ]

    # ── 选择逻辑 ──

    def _selectable_items(self) -> list[tuple[int, MenuItem]]:
        return [(i, item) for i, item in enumerate(self.items) if item.group != "header"]

    def _selectable_index(self) -> int:
        for idx, (i, _) in enumerate(self._selectable_items()):
            if i == self.selected:
                return idx
        return 0

    def move_up(self) -> None:
        selectable = self._selectable_items()
        idx = self._selectable_index()
        self.selected = selectable[(idx - 1) % len(selectable)][0]

    def move_down(self) -> None:
        selectable = self._selectable_items()
        idx = self._selectable_index()
        self.selected = selectable[(idx + 1) % len(selectable)][0]

    def page_up(self) -> None:
        selectable = self._selectable_items()
        idx = self._selectable_index()
        new_idx = max(0, idx - _SCROLL_SPEED)
        self.selected = selectable[new_idx][0]

    def page_down(self) -> None:
        selectable = self._selectable_items()
        idx = self._selectable_index()
        new_idx = min(len(selectable) - 1, idx + _SCROLL_SPEED)
        self.selected = selectable[new_idx][0]

    def get_selected_action(self) -> str:
        return self.items[self.selected].action

    def quit(self) -> None:
        self.running = False

    # ── 缓存 ──

    def _get_config(self) -> dict[str, object]:
        now = time.time()
        if now - self._config_cache_time > _REFRESH_INTERVAL:
            self._config_cache = load_config(CONFIG_PATH)
            self._config_cache_time = now
        return self._config_cache

    def _get_active(self) -> bool:
        now = time.time()
        if now - self._active_cache_time > _REFRESH_INTERVAL:
            self._active_cache = service_is_active()
            self._active_cache_time = now
        return self._active_cache

    def _get_latency(self) -> LatencyInfo:
        return self._latency

    def _update_latency_async(self) -> None:
        """异步更新延迟和出口 IP"""
        config = self._get_config()
        port = int(str(config.get('local_port', 1080)))
        try:
            from autosocks.core.tunnel import check_proxy, get_exit_ip
            start = time.monotonic()
            ok = check_proxy(port)
            elapsed = (time.monotonic() - start) * 1000
            if ok:
                exit_ip = get_exit_ip(port)
                self._latency = LatencyInfo(ms=elapsed, exit_ip=exit_ip, timestamp=time.time())
            else:
                self._latency = LatencyInfo(ms=-1.0, exit_ip=None, timestamp=time.time())
        except Exception:
            self._latency = LatencyInfo(ms=-1.0, exit_ip=None, timestamp=time.time())

    # ── 运行入口 ──

    def run(self) -> None:
        if os.getenv("TERM") is None:
            return
        curses.wrapper(self._main_loop)

    def _init_colors(self) -> None:
        try:
            curses.use_default_colors()
            # 使用 -1 背景表示透明/终端默认背景色
            curses.init_pair(_CLR_TITLE, curses.COLOR_CYAN, -1)
            curses.init_pair(_CLR_RUNNING, curses.COLOR_GREEN, -1)
            curses.init_pair(_CLR_STOPPED, curses.COLOR_RED, -1)
            curses.init_pair(_CLR_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(_CLR_GROUP, curses.COLOR_YELLOW, -1)
            curses.init_pair(_CLR_MSG, curses.COLOR_WHITE, -1)
            curses.init_pair(_CLR_KEYBAR, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(_CLR_BORDER, curses.COLOR_BLUE, -1)
            curses.init_pair(_CLR_DIM, curses.COLOR_WHITE, -1)          # 配合 A_DIM 使用
            curses.init_pair(_CLR_SUCCESS, curses.COLOR_GREEN, -1)
            curses.init_pair(_CLR_ERROR, curses.COLOR_RED, -1)
            curses.init_pair(_CLR_HINT, curses.COLOR_CYAN, -1)
            curses.init_pair(_CLR_WARN, curses.COLOR_YELLOW, -1)
            curses.init_pair(_CLR_ACCENT, curses.COLOR_MAGENTA, -1)
            curses.init_pair(_CLR_VALUE, curses.COLOR_WHITE, -1)       # 配合 A_BOLD 使用
            curses.init_pair(_CLR_DLG_BORDER, curses.COLOR_CYAN, -1)
            curses.init_pair(_CLR_DLG_TITLE, curses.COLOR_YELLOW, -1)
            curses.init_pair(_CLR_DLG_INPUT, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(_CLR_MENU_DIM, curses.COLOR_WHITE, -1)    # 配合 A_DIM 使用
        except curses.error:
            pass

    def _main_loop(self, stdscr: curses.window) -> None:
        self._stdscr = stdscr
        self._init_colors()
        curses.curs_set(0)
        curses.noecho()
        stdscr.nodelay(True)
        stdscr.keypad(True)

        self._config_cache_time = 0.0
        self._active_cache_time = 0.0
        self._spawn_latency_check()

        while self.running:
            try:
                now = time.time()
                if now - self._latency.timestamp > _LATENCY_INTERVAL:
                    self._spawn_latency_check()
                    self._dirty = True

                if self._latency.timestamp != self._last_latency_ts:
                    self._dirty = True

                if self._dirty and now - self._last_draw > 0.05:
                    self._draw(stdscr)
                    self._last_draw = now
                    self._last_latency_ts = self._latency.timestamp
                    self._dirty = False

                key = stdscr.getch()
                if key == curses.KEY_RESIZE:
                    # 终端窗口缩放 → 强制全量重绘
                    self._dirty = True
                    self._last_draw = 0.0
                elif key != -1:
                    self._handle_key(key, stdscr)
                    self._dirty = True
                else:
                    time.sleep(0.02)
            except KeyboardInterrupt:
                self.running = False

    def _spawn_latency_check(self) -> None:
        """启动后台线程检测延迟"""
        if self._get_active():
            t = threading.Thread(target=self._update_latency_async, daemon=True)
            t.start()
        else:
            self._latency = LatencyInfo(ms=-1.0, exit_ip=None, timestamp=time.time())

    # ── 绘制核心 ──

    def _safe_addstr(self, stdscr: curses.window, y: int, x: int, text: str, attr: int = 0) -> None:
        height, width = stdscr.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= width:
            return
        max_len = width - x
        if max_len <= 0:
            return
        text = text[:max_len]
        if not text:
            return
        try:
            stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def _draw(self, stdscr: curses.window) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if height < 10 or width < 40:
            self._safe_addstr(stdscr, 0, 0, "终端太小，请调整窗口大小")
            stdscr.refresh()
            return

        menu_w = min(self._menu_width, width // 2)
        panel_x = menu_w + 2
        panel_w = width - panel_x - 2

        # ── 顶栏（双层设计）──
        # 第一行：装饰标题栏
        top_line = "╭" + "─" * (width - 2) + "╮"
        self._safe_addstr(stdscr, 0, 0, top_line, curses.color_pair(_CLR_BORDER))

        # 标题区（左） + 状态指示器（右）
        title = f" ◈ AutoSOCKS  v{__version__} "
        self._safe_addstr(stdscr, 1, 0, "│", curses.color_pair(_CLR_BORDER))
        self._safe_addstr(stdscr, 1, 2, title, curses.color_pair(_CLR_TITLE) | curses.A_BOLD)

        active = self._get_active()
        status_text = "● 运行中" if active else "○ 已停止"
        status_clr = _CLR_RUNNING if active else _CLR_STOPPED
        status_x = width - len(status_text) - 3
        self._safe_addstr(stdscr, 1, status_x, status_text,
                          curses.color_pair(status_clr) | curses.A_BOLD)
        self._safe_addstr(stdscr, 1, width - 1, "│", curses.color_pair(_CLR_BORDER))

        # 分隔线
        self._safe_addstr(stdscr, 2, 0, "├" + "─" * (width - 2) + "┤", curses.color_pair(_CLR_BORDER))

        # 左/右面板分隔线
        for row in range(3, height - 2):
            self._safe_addstr(stdscr, row, menu_w + 1, "│", curses.color_pair(_CLR_BORDER))

        self._draw_menu(stdscr, 3, 1, menu_w, height - 4)
        self._draw_status_panel(stdscr, panel_x, 3, panel_w, height - 4, active)

        if self.message:
            elapsed = time.time() - self.message_time
            if elapsed > _MSG_TIMEOUT:
                self.message = ""
                self._dirty = True
            else:
                msg_y = height - 9
                if msg_y > 3:
                    self._draw_message(stdscr, panel_x, msg_y, panel_w)

        self._safe_addstr(stdscr, height - 2, 0, "├" + "─" * (width - 2) + "┤",
                          curses.color_pair(_CLR_BORDER))

        keybar = (
            " │↑↓ 移动  │  ↵ 选择  │  "
            "s 启动  │  S 停止  │  r 重启  │  "
            "d 后台  │  q 退出  │  "
            "F1 帮助  │  F5 刷新  │  "
            "^E 自启  │  ^U 卸载  │"
        )
        keybar_full = keybar + " " * max(0, width - len(keybar) - 3)
        self._safe_addstr(stdscr, height - 1, 0, "│", curses.color_pair(_CLR_BORDER))
        self._safe_addstr(stdscr, height - 1, 1, keybar_full[:width - 2],
                          curses.color_pair(_CLR_KEYBAR))
        self._safe_addstr(stdscr, height - 1, width - 1, "│", curses.color_pair(_CLR_BORDER))

        stdscr.refresh()

    def _draw_menu(self, stdscr: curses.window, y_start: int, x: int, w: int, y_end: int) -> None:
        """绘制左侧菜单 - 精致风格"""
        visible_height = y_end - y_start
        total_items = len(self.items)

        sel_row = self.selected
        if sel_row < self._scroll_offset:
            self._scroll_offset = sel_row
        elif sel_row >= self._scroll_offset + visible_height:
            self._scroll_offset = sel_row - visible_height + 1

        # 菜单区域左边框
        for row in range(y_start, y_end):
            self._safe_addstr(stdscr, row, x, " ", 0)

        row = y_start
        for i in range(self._scroll_offset, min(total_items, self._scroll_offset + visible_height)):
            item = self.items[i]
            if row >= y_end:
                break

            if item.group == "header":
                # 分组标题：装饰线 + 文字
                inner = f"  {item.label.strip(' ─')}"
                deco_w = max(2, w - len(inner) - 1)
                deco = "─" * deco_w
                header_line = f" {inner} {deco}"
                attr = curses.color_pair(_CLR_GROUP) | curses.A_BOLD
                self._safe_addstr(stdscr, row, x, header_line[:w], attr)
            elif i == self.selected:
                # 选中项：深色背景高亮条
                label = item.label.strip()
                pad = w - len(label) - 3
                full = f" ▸ {label}{' ' * max(0, pad)}"
                self._safe_addstr(stdscr, row, x, " " * w,
                                  curses.color_pair(_CLR_SELECTED))
                self._safe_addstr(stdscr, row, x, full[:w],
                                  curses.color_pair(_CLR_SELECTED) | curses.A_BOLD)
            else:
                # 未选中项：暗色弱化
                label = item.label.strip()
                attr = curses.color_pair(_CLR_MENU_DIM) | curses.A_DIM
                self._safe_addstr(stdscr, row, x, f"   {label}"[:w], attr)
            row += 1

        # 滚动指示器
        if self._scroll_offset > 0:
            self._safe_addstr(stdscr, y_start, x + w - 1, "▲", curses.color_pair(_CLR_BORDER) | curses.A_BOLD)
        if self._scroll_offset + visible_height < total_items:
            self._safe_addstr(stdscr, y_end - 1, x + w - 1, "▼", curses.color_pair(_CLR_BORDER) | curses.A_BOLD)

    def _draw_status_panel(self, stdscr: curses.window, x: int, y_start: int, w: int,
                           y_end: int, active: bool) -> None:
        """绘制右侧状态面板 - 分区卡片式设计"""
        if w < 12:
            return

        config = self._get_config()
        latency = self._get_latency()
        y = y_start

        # ═══ 分区 1：服务状态 ═══
        self._safe_addstr(stdscr, y, x, "╭" + "─" * (w - 2) + "╮", curses.color_pair(_CLR_BORDER))
        y += 1
        label = " 状态面板 "
        self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
        self._safe_addstr(stdscr, y, x + (w - len(label)) // 2, label,
                          curses.color_pair(_CLR_TITLE) | curses.A_BOLD)
        self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
        y += 1
        self._safe_addstr(stdscr, y, x, "├" + "─" * (w - 2) + "┤", curses.color_pair(_CLR_BORDER))
        y += 1

        # 服务状态行
        icon = "●" if active else "○"
        status_text = "运行中" if active else "未运行"
        clr = _CLR_RUNNING if active else _CLR_STOPPED
        line_content = f"  {icon} 服务 {status_text}"
        self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
        self._safe_addstr(stdscr, y, x + 2, line_content, curses.color_pair(clr) | curses.A_BOLD)
        self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
        y += 1

        # 延迟/出口 IP
        if active and latency.ms >= 0:
            lat_str = f"{latency.ms:.0f}ms"
            lat_clr = _CLR_RUNNING if latency.ms < 200 else (_CLR_WARN if latency.ms < 500 else _CLR_STOPPED)
            self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
            self._safe_addstr(stdscr, y, x + 2, f"  ⟐ 延迟 {lat_str}",
                              curses.color_pair(lat_clr) | curses.A_BOLD)
            if latency.exit_ip:
                ip = str(latency.exit_ip)
                ip_x = x + 18
                self._safe_addstr(stdscr, y, ip_x, f"出口 {ip}"[:w - (ip_x - x) - 1],
                                  curses.color_pair(_CLR_VALUE))
            self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
            y += 1
            # 延迟条形图
            bar_w = min(w - 8, 24)
            ratio = min(latency.ms / 500.0, 1.0)
            filled = int(bar_w * ratio)
            empty = bar_w - filled
            bar = "█" * filled + "░" * empty
            self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
            self._safe_addstr(stdscr, y, x + 4, bar, curses.color_pair(lat_clr) | curses.A_BOLD)
            self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
        elif active:
            self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
            self._safe_addstr(stdscr, y, x + 2, "  ⟐ 检测中...", curses.color_pair(_CLR_HINT) | curses.A_DIM)
            self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
        else:
            self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
            self._safe_addstr(stdscr, y, x + 2, " " * (w - 3), 0)
            self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
        y += 1

        # ═══ 分区 2：连接信息 ═══
        self._safe_addstr(stdscr, y, x, "├" + "─" * (w - 2) + "┤", curses.color_pair(_CLR_BORDER))
        y += 1

        server = f"{config.get('server_user', 'root')}@{config.get('server_host', '未配置')}"
        local_port = str(config.get('local_port', 1080))
        local_bind = str(config.get('local_bind', '127.0.0.1'))
        auth_type = str(config.get('auth_type', 'key'))

        rows_info = [
            ("远程主机", server),
            ("SSH 端口", str(config.get('server_port', 22))),
            ("本地监听", f"{local_bind}:{local_port}"),
            ("认证方式", "SSH 密钥" if auth_type == "key" else "密码认证"),
        ]
        for label, value in rows_info:
            self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
            self._safe_addstr(stdscr, y, x + 2, f"  {label}", curses.color_pair(_CLR_ACCENT) | curses.A_BOLD)
            self._safe_addstr(stdscr, y, x + 14, value[:w - 16], curses.color_pair(_CLR_VALUE))
            self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
            y += 1

        # ═══ 分区 3：SSH / 重连 / 日志 ═══
        self._safe_addstr(stdscr, y, x, "├" + "─" * (w - 2) + "┤", curses.color_pair(_CLR_BORDER))
        y += 1

        keepalive = str(config.get('ssh_keepalive', 60))
        timeout = str(config.get('ssh_timeout', 10))
        self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
        self._safe_addstr(stdscr, y, x + 2, f"  心跳 {keepalive}s    超时 {timeout}s",
                          curses.color_pair(_CLR_HINT) | curses.A_DIM)
        self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
        y += 1

        recon = "●" if config.get('reconnect_enabled', True) else "○"
        recon_int = str(config.get('reconnect_interval', 3))
        log_on = "●" if config.get('log_enabled', True) else "○"
        self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
        self._safe_addstr(stdscr, y, x + 2, f"  重连 {recon} {recon_int}s    日志 {log_on}",
                          curses.color_pair(_CLR_HINT) | curses.A_DIM)
        self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
        y += 1

        # ═══ 分区 4：代理地址 ═══
        self._safe_addstr(stdscr, y, x, "├" + "─" * (w - 2) + "┤", curses.color_pair(_CLR_BORDER))
        y += 1

        proxy = f"socks5://{local_bind}:{local_port}"
        http_port = int(local_port) + 1
        http_proxy = f"http://{local_bind}:{http_port}"

        self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
        self._safe_addstr(stdscr, y, x + 2, f"  {proxy}"[:w - 4],
                          curses.color_pair(_CLR_VALUE) | curses.A_BOLD)
        self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
        y += 1
        self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
        self._safe_addstr(stdscr, y, x + 2, f"  {http_proxy}"[:w - 4],
                          curses.color_pair(_CLR_HINT) | curses.A_DIM)
        self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
        y += 1

        # 快速使用提示
        y += 1
        if y + 1 < y_end:
            self._safe_addstr(stdscr, y, x, "│", curses.color_pair(_CLR_BORDER))
            self._safe_addstr(stdscr, y, x + 2, "  eval \"$(autosocks env)\"",
                              curses.color_pair(_CLR_HINT))
            self._safe_addstr(stdscr, y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
            y += 1

        # 底部闭合
        panel_bottom = y_end - 5
        if panel_bottom > y:
            for fill_y in range(y, panel_bottom):
                self._safe_addstr(stdscr, fill_y, x, "│", curses.color_pair(_CLR_BORDER))
                self._safe_addstr(stdscr, fill_y, x + w - 1, "│", curses.color_pair(_CLR_BORDER))
            y = panel_bottom
        self._safe_addstr(stdscr, y, x, "╰" + "─" * (w - 2) + "╯", curses.color_pair(_CLR_BORDER))

    def _draw_message(self, stdscr: curses.window, x: int, y: int, w: int) -> None:
        """绘制 Toast 轻量提示条 — 3 秒自动消失，不遮挡界面"""
        if not self.message or w < 12:
            return

        # 自动推断消息类型
        clr = _CLR_MSG
        kw_success = ("已启动", "已停止", "已重启", "成功", "已保存", "已安装", "已注册")
        kw_error = ("失败", "错误", "需要", "未检测到", "无法")
        kw_warn = ("取消", "跳过")
        if any(kw in self.message for kw in kw_success):
            clr = _CLR_SUCCESS
        elif any(kw in self.message for kw in kw_error):
            clr = _CLR_ERROR
        elif any(kw in self.message for kw in kw_warn):
            clr = _CLR_WARN

        # 简洁单行 Toast
        toast = f" {self.message.strip()} "
        toast = toast[:w - 4]
        self._safe_addstr(stdscr, y, x + (w - len(toast)) // 2, toast,
                          curses.color_pair(clr) | curses.A_REVERSE | curses.A_BOLD)

    # ── 对话框边框绘制辅助 ──

    def _draw_dlg_frame(self, stdscr: curses.window, dlg_y: int, dlg_x: int,
                        dlg_w: int, dlg_h: int, title: str) -> None:
        """绘制对话框边框和标题（静态部分）"""
        # 顶部边框 + 标题
        title_str = f" {title} "
        self._safe_addstr(stdscr, dlg_y, dlg_x,
                          "╭" + "─" * ((dlg_w - len(title_str) - 2) // 2) + title_str
                          + "─" * ((dlg_w - len(title_str) - 1) // 2) + "╮",
                          curses.color_pair(_CLR_DLG_BORDER))
        # 侧边
        for dy in range(1, dlg_h - 1):
            self._safe_addstr(stdscr, dlg_y + dy, dlg_x, "│", curses.color_pair(_CLR_DLG_BORDER))
            self._safe_addstr(stdscr, dlg_y + dy, dlg_x + dlg_w - 1, "│",
                              curses.color_pair(_CLR_DLG_BORDER))
        # 底部边框
        self._safe_addstr(stdscr, dlg_y + dlg_h - 1, dlg_x,
                          "╰" + "─" * (dlg_w - 2) + "╯", curses.color_pair(_CLR_DLG_BORDER))

    # ── curses 对话框原语 ──

    def _dialog_input(self, stdscr: curses.window, title: str, default: str = "",
                      password: bool = False) -> str | None:
        """在 TUI 内弹出输入对话框，返回输入值或 None（取消）。优化版：增量重绘。"""
        height, width = stdscr.getmaxyx()
        if height < 8 or width < 20:
            return default

        dlg_w = min(56, width - 4)
        dlg_h = 7
        dlg_x = (width - dlg_w) // 2
        dlg_y = (height - dlg_h) // 2

        value = default
        cursor_pos = len(value)
        input_y = dlg_y + 3
        input_x = dlg_x + 3
        input_w = dlg_w - 6

        def _draw_static() -> None:
            """只绘制静态元素（边框、标题、提示）"""
            for dy in range(dlg_h):
                self._safe_addstr(stdscr, dlg_y + dy, dlg_x, " " * dlg_w,
                                  curses.color_pair(_CLR_DLG_INPUT))
            self._draw_dlg_frame(stdscr, dlg_y, dlg_x, dlg_w, dlg_h, title)
            if default and not password:
                self._safe_addstr(stdscr, dlg_y + 2, dlg_x + 2,
                                  f"（默认: {default}）", curses.color_pair(_CLR_HINT) | curses.A_DIM)
            self._safe_addstr(stdscr, dlg_y + 5, dlg_x + 2,
                              " ↵ 确认  Esc 取消", curses.color_pair(_CLR_HINT) | curses.A_DIM)

        def _draw_input() -> None:
            """只更新输入框区域"""
            if password:
                masked = "*" * len(value)
                display = masked if len(masked) <= input_w else masked[-input_w:]
            else:
                display = value if len(value) <= input_w else value[-input_w:]
            self._safe_addstr(stdscr, input_y, input_x,
                              display + " " * (input_w - len(display)),
                              curses.color_pair(_CLR_DLG_INPUT))
            try:
                stdscr.move(input_y, input_x + min(cursor_pos, input_w))
            except curses.error:
                pass

        _draw_static()
        _draw_input()
        stdscr.refresh()

        while True:
            curses.curs_set(1)
            if not password:
                curses.echo()
            stdscr.nodelay(False)

            key = stdscr.getch()

            stdscr.nodelay(True)
            curses.noecho()
            curses.curs_set(0)

            if key == ord("\n") or key == curses.KEY_ENTER:
                return value if value else default
            if key == 27:  # ESC
                return None
            if key in (curses.KEY_BACKSPACE, 127, 8):
                if cursor_pos > 0:
                    value = value[:cursor_pos - 1] + value[cursor_pos:]
                    cursor_pos -= 1
                    _draw_input()
                    stdscr.refresh()
            elif key == curses.KEY_DC:
                if cursor_pos < len(value):
                    value = value[:cursor_pos] + value[cursor_pos + 1:]
                    _draw_input()
                    stdscr.refresh()
            elif key == curses.KEY_LEFT:
                cursor_pos = max(0, cursor_pos - 1)
                _draw_input()
                stdscr.refresh()
            elif key == curses.KEY_RIGHT:
                cursor_pos = min(len(value), cursor_pos + 1)
                _draw_input()
                stdscr.refresh()
            elif key == curses.KEY_HOME:
                cursor_pos = 0
                _draw_input()
                stdscr.refresh()
            elif key == curses.KEY_END:
                cursor_pos = len(value)
                _draw_input()
                stdscr.refresh()
            elif key == ord("\t"):
                pass  # 忽略 Tab
            elif 32 <= key < 127:
                if len(value) < 200:
                    value = value[:cursor_pos] + chr(key) + value[cursor_pos:]
                    cursor_pos += 1
                    _draw_input()
                    stdscr.refresh()

    def _dialog_select(self, stdscr: curses.window, title: str, options: list[str],
                       default: int = 0) -> int | None:
        """在 TUI 内弹出选择对话框，返回选中索引或 None（取消）。优化版：增量重绘。"""
        if not options:
            return None
        height, width = stdscr.getmaxyx()
        dlg_w = min(50, width - 4)
        dlg_h = min(len(options) + 5, height - 4)
        dlg_x = (width - dlg_w) // 2
        dlg_y = (height - dlg_h) // 2

        selected = default
        scroll = max(0, selected - (dlg_h - 5))

        def _draw_static() -> None:
            for dy in range(dlg_h):
                self._safe_addstr(stdscr, dlg_y + dy, dlg_x, " " * dlg_w,
                                  curses.color_pair(_CLR_DLG_INPUT))
            self._draw_dlg_frame(stdscr, dlg_y, dlg_x, dlg_w, dlg_h, title)

        def _draw_all() -> None:
            _draw_static()
            visible_count = dlg_h - 4
            for i in range(visible_count):
                idx = scroll + i
                if idx >= len(options):
                    break
                opt_y = dlg_y + 3 + i
                marker = "▸ " if idx == selected else "  "
                line_text = f"{marker}{idx + 1}. {options[idx]}"
                attr = (curses.color_pair(_CLR_SELECTED) | curses.A_BOLD) if idx == selected \
                    else curses.color_pair(_CLR_DIM)
                self._safe_addstr(stdscr, opt_y, dlg_x + 2, line_text[:dlg_w - 4], attr)
            self._safe_addstr(stdscr, dlg_y + dlg_h - 2, dlg_x + 2,
                              " ↵ 确认  ↑↓ 选择  Esc 取消", curses.color_pair(_CLR_DIM))

        _draw_all()
        stdscr.refresh()

        while True:
            curses.curs_set(0)
            stdscr.nodelay(False)

            key = stdscr.getch()

            stdscr.nodelay(True)

            if key == ord("\n") or key == curses.KEY_ENTER:
                return selected
            if key == 27:
                return None
            if key in (curses.KEY_UP, ord("k")):
                old = selected
                if selected > 0:
                    selected -= 1
                    if selected < scroll:
                        scroll = selected
                if selected != old:
                    _draw_all()
                    stdscr.refresh()
            elif key in (curses.KEY_DOWN, ord("j")):
                old = selected
                if selected < len(options) - 1:
                    selected += 1
                    visible_count = dlg_h - 4
                    if selected >= scroll + visible_count:
                        scroll = selected - visible_count + 1
                if selected != old:
                    _draw_all()
                    stdscr.refresh()

    # ── 多字段表单对话框 ──

    def _dialog_form(self, stdscr: curses.window, title: str,
                     fields: list[tuple[str, str, object, str, list[str] | None]],
                     help_lines: list[str] | None = None) -> dict[str, object] | None:
        """多字段表单对话框 — 内联编辑版。

        按 Enter 直接在表单内编辑字段值（不弹出子对话框），
        提供流畅的一体化编辑体验。

        Args:
            title: 表单标题
            fields: [(key, label, value, field_type, options), ...]
            help_lines: 底部帮助文本（可选）

        Returns:
            更新后的值字典 {key: value}，取消返回 None
        """
        height, width = stdscr.getmaxyx()
        if height < 8 or width < 20:
            return None

        label_w = max(len(lbl) for _, lbl, _, _, _ in fields) + 2
        n_fields = len(fields)
        n_help = len(help_lines) + 1 if help_lines else 0
        dlg_w = min(max(52, label_w + 30), width - 4)
        dlg_h = min(n_fields + n_help + 7, height - 4)
        dlg_x = (width - dlg_w) // 2
        dlg_y = (height - dlg_h) // 2

        _ICONS  = {"text": "✎", "number": "#", "password": "●", "select": "▼", "bool": "✓"}
        _VAL_X  = dlg_x + label_w + 6          # 值起始列
        _VAL_W  = dlg_w - label_w - 10         # 值最大宽度

        values   = {k: v for k, _, v, _, _ in fields}
        cursor   = 0
        prev_cursor = 0
        modified = False

        # ── 内联编辑状态 ──
        editing  = False           # 是否处于内联编辑模式
        edit_buf = ""              # 编辑缓冲区
        edit_pos = 0               # 编辑光标位置
        edit_key = ""              # 当前编辑的字段 key

        def _fmt_value(key: str, ft: str, opts: list[str] | None) -> str:
            val = values.get(key, "")
            if ft == "password":
                return "*" * min(len(str(val)), 12)
            if ft == "bool":
                return "是" if val else "否"
            if ft == "select" and opts:
                try:
                    idx = int(str(val))
                    if 0 <= idx < len(opts):
                        return opts[idx]
                except (ValueError, TypeError):
                    for _, o in enumerate(opts):
                        if str(o) == str(val):
                            return o
            return str(val)

        # ── 绘制函数 ──

        def _draw_field(i: int, is_cursor: bool, edit_mode: bool = False) -> None:
            """绘制单个字段行。edit_mode=True 时显示内联编辑状态。"""
            key, label, _, ft, opts = fields[i]
            frow = dlg_y + 3 + i
            icon = _ICONS.get(ft, " ")

            if is_cursor:
                label_base = curses.color_pair(_CLR_DLG_INPUT) | curses.A_BOLD
                val_base   = curses.color_pair(_CLR_DLG_INPUT) | curses.A_BOLD
            else:
                label_base = curses.color_pair(_CLR_ACCENT)
                val_base   = curses.color_pair(_CLR_VALUE)

            # 清空整行
            self._safe_addstr(stdscr, frow, dlg_x + 1, " " * (dlg_w - 2),
                              curses.color_pair(_CLR_DLG_INPUT) if (is_cursor and not edit_mode)
                              else curses.color_pair(_CLR_DLG_INPUT) | curses.A_DIM)

            # 图标
            self._safe_addstr(stdscr, frow, dlg_x + 2, icon, label_base)

            # 标签
            lbl_text = f" {label}："
            self._safe_addstr(stdscr, frow, dlg_x + 4, lbl_text, label_base)

            if edit_mode and is_cursor:
                # ── 内联编辑渲染 ──
                field_w = min(_VAL_W, dlg_w - label_w - 7)

                # 绘制编辑值文本
                self._safe_addstr(stdscr, frow, _VAL_X, " " * field_w,
                                  curses.color_pair(_CLR_DLG_INPUT) | curses.A_BOLD)
                display = edit_buf
                if ft == "password":
                    display = "*" * len(edit_buf)
                if edit_pos < len(display):
                    prefix = display[:edit_pos]
                    ch     = display[edit_pos]
                    suffix = display[edit_pos + 1:]
                else:
                    prefix = display
                    ch     = " "
                    suffix = ""
                # 截断适配宽度
                if len(display) > field_w - 1:
                    # 滚动：保持光标在视图内
                    visible_start = max(0, edit_pos - field_w // 2)
                    visible_start = min(visible_start, max(0, len(display) - field_w + 2))
                    prefix = display[visible_start:edit_pos]
                    ch     = display[edit_pos] if edit_pos < len(display) else " "
                    suffix = display[edit_pos + 1:visible_start + field_w - 1]

                self._safe_addstr(stdscr, frow, _VAL_X, prefix, val_base)
                self._safe_addstr(stdscr, frow, _VAL_X + len(prefix), ch,
                                  curses.A_REVERSE | val_base)
                if suffix:
                    self._safe_addstr(stdscr, frow, _VAL_X + len(prefix) + 1, suffix, val_base)
            else:
                # ── 普通显示渲染 ──
                val_str = _fmt_value(key, ft, opts)
                if len(val_str) > _VAL_W:
                    val_str = val_str[:_VAL_W - 2] + "…"
                self._safe_addstr(stdscr, frow, _VAL_X, val_str, val_base)

            # 类型标记（右对齐）
            if ft != "text":
                tag = {"password": "(密码)", "number": "(数字)", "select": "▼", "bool": "◉"}.get(ft, "")
                tag_x = dlg_x + dlg_w - len(tag) - 4
                tag_col = label_base if is_cursor else curses.color_pair(_CLR_HINT)
                self._safe_addstr(stdscr, frow, tag_x, tag, tag_col)

        def _draw_status(msg: str = "", clr: int = _CLR_HINT) -> None:
            """绘制底部状态栏"""
            bar_y = dlg_y + dlg_h - 2
            # 左侧状态
            left = msg if msg else ("● 已修改" if modified else "")
            self._safe_addstr(stdscr, bar_y, dlg_x + 2, left[:18],
                              curses.color_pair(clr) | curses.A_BOLD)
            # 右侧快捷键
            if editing:
                keys = "↵确认  Esc放弃"
            else:
                keys = "↵编辑  S保存  Esc返回  ↑↓移动"
            kx = dlg_x + dlg_w - len(keys) - 3
            self._safe_addstr(stdscr, bar_y, kx, keys,
                              curses.color_pair(_CLR_KEYBAR))

        def _draw_all() -> None:
            """完整重绘"""
            for dy in range(dlg_h):
                self._safe_addstr(stdscr, dlg_y + dy, dlg_x, " " * dlg_w,
                                  curses.color_pair(_CLR_DLG_INPUT))
            self._draw_dlg_frame(stdscr, dlg_y, dlg_x, dlg_w, dlg_h, title)

            # 字段区域背景
            for dy in range(3, dlg_h - 2):
                self._safe_addstr(stdscr, dlg_y + dy, dlg_x + 1, " " * (dlg_w - 2),
                                  curses.color_pair(_CLR_DLG_INPUT) | curses.A_DIM)

            # 分隔线
            sep_y = dlg_y + 2
            self._safe_addstr(stdscr, sep_y, dlg_x + 1, "─" * (dlg_w - 2),
                              curses.color_pair(_CLR_DLG_BORDER) | curses.A_DIM)

            for i in range(n_fields):
                _draw_field(i, i == cursor, editing and i == cursor)

            # 帮助文本
            if help_lines:
                hs = dlg_y + dlg_h - 3 - len(help_lines)
                for j, line in enumerate(help_lines):
                    self._safe_addstr(stdscr, hs + j, dlg_x + 2,
                                      f"ℹ {line}"[:dlg_w - 4],
                                      curses.color_pair(_CLR_HINT) | curses.A_DIM)

            _draw_status()

        # ── 初始渲染 ──
        _draw_all()
        stdscr.refresh()

        # ── 事件循环 ──
        while True:
            curses.curs_set(1 if editing else 0)
            stdscr.nodelay(False)
            key = stdscr.getch()
            stdscr.nodelay(True)

            # ═══════════════════════════════════════
            # 内联编辑模式 — 按键处理
            # ═══════════════════════════════════════
            if editing:
                ft = fields[cursor][3]
                if key == 27:  # Esc — 放弃编辑
                    editing = False
                    _draw_field(cursor, True)
                    _draw_status()
                    stdscr.refresh()
                    continue
                if key in (ord("\n"), curses.KEY_ENTER):
                    # 提交编辑
                    new_val = edit_buf.strip()
                    if ft == "number" and new_val:
                        try:
                            values[edit_key] = int(new_val)
                            modified = True
                        except ValueError:
                            _draw_status("✗ 请输入有效数字", _CLR_ERROR)
                            stdscr.refresh()
                            curses.napms(800)
                            _draw_status()
                            stdscr.refresh()
                            continue
                    else:
                        if new_val != str(values.get(edit_key, "")):
                            values[edit_key] = new_val
                            modified = True
                    editing = False
                    _draw_field(cursor, True)
                    _draw_status()
                    stdscr.refresh()
                    continue
                if key in (curses.KEY_BACKSPACE, 127, 8):
                    if edit_pos > 0:
                        edit_buf = edit_buf[:edit_pos - 1] + edit_buf[edit_pos:]
                        edit_pos -= 1
                elif key == curses.KEY_DC:
                    if edit_pos < len(edit_buf):
                        edit_buf = edit_buf[:edit_pos] + edit_buf[edit_pos + 1:]
                elif key == curses.KEY_LEFT:
                    edit_pos = max(0, edit_pos - 1)
                elif key == curses.KEY_RIGHT:
                    edit_pos = min(len(edit_buf), edit_pos + 1)
                elif key == curses.KEY_HOME:
                    edit_pos = 0
                elif key == curses.KEY_END:
                    edit_pos = len(edit_buf)
                elif key == ord("\t"):
                    pass
                elif 32 <= key < 127:
                    if len(edit_buf) < 200:
                        edit_buf = edit_buf[:edit_pos] + chr(key) + edit_buf[edit_pos:]
                        edit_pos += 1
                _draw_field(cursor, True, True)
                stdscr.refresh()
                continue

            # ═══════════════════════════════════════
            # 导航模式 — 按键处理
            # ═══════════════════════════════════════
            if key == 27:  # Esc
                if modified:
                    choice = self._dialog_select(stdscr, "有未保存的修改",
                                                 ["放弃修改并退出", "继续编辑"], 1)
                    if choice == 1:
                        _draw_all()
                        stdscr.refresh()
                        continue
                return None

            if key in (curses.KEY_UP, ord("k")):
                prev_cursor, cursor = cursor, (cursor - 1) % n_fields
                _draw_field(prev_cursor, False)
                _draw_field(cursor, True)
                stdscr.refresh()

            elif key in (curses.KEY_DOWN, ord("j"), ord("\t")):
                prev_cursor, cursor = cursor, (cursor + 1) % n_fields
                _draw_field(prev_cursor, False)
                _draw_field(cursor, True)
                stdscr.refresh()

            elif key in (curses.KEY_HOME, ord("g")) and cursor > 0:
                prev_cursor, cursor = cursor, 0
                _draw_field(prev_cursor, False)
                _draw_field(cursor, True)
                stdscr.refresh()

            elif key in (curses.KEY_END, ord("G")):
                prev_cursor, cursor = cursor, n_fields - 1
                _draw_field(prev_cursor, False)
                _draw_field(cursor, True)
                stdscr.refresh()

            elif key == ord("\n") or key == curses.KEY_ENTER:
                kv, klabel, _, kft, kopts = fields[cursor]

                if kft == "bool":
                    # 布尔值：即时翻转
                    values[kv] = not bool(values.get(kv, False))
                    modified = True
                    _draw_field(cursor, True)
                    _draw_status()
                    stdscr.refresh()

                elif kft == "select" and kopts:
                    # 选择字段：弹出选择列表
                    cur_idx = int(str(values.get(kv, 0)))
                    new_idx = self._dialog_select(stdscr, f"选择 {klabel}", kopts, cur_idx)
                    if new_idx is not None and new_idx != cur_idx:
                        values[kv] = new_idx
                        modified = True
                    _draw_all()
                    stdscr.refresh()

                else:
                    # 文本/数字/密码：进入内联编辑模式
                    editing  = True
                    edit_key = kv
                    edit_buf = str(values.get(kv, ""))
                    edit_pos = len(edit_buf)
                    _draw_field(cursor, True, True)
                    _draw_status()
                    stdscr.refresh()

            elif key == ord("s") or key == ord("S"):
                # 保存
                _draw_status("✓ 已保存！", _CLR_SUCCESS)
                keys_prompt = "  按任意键关闭"
                kx = dlg_x + dlg_w - len(keys_prompt) - 3
                self._safe_addstr(stdscr, dlg_y + dlg_h - 2, kx, keys_prompt,
                                  curses.color_pair(_CLR_HINT))
                stdscr.refresh()
                curses.napms(400)
                stdscr.nodelay(False)
                stdscr.getch()
                stdscr.nodelay(True)
                return values

    def _dialog_message(self, stdscr: curses.window, title: str, lines: list[str],
                        clr: int = _CLR_MSG) -> None:
        """在 TUI 内弹出信息对话框，按任意键关闭"""
        height, width = stdscr.getmaxyx()
        dlg_w = min(60, width - 4)
        dlg_h = min(len(lines) + 5, height - 4)
        dlg_x = (width - dlg_w) // 2
        dlg_y = (height - dlg_h) // 2

        while True:
            for dy in range(dlg_h):
                self._safe_addstr(stdscr, dlg_y + dy, dlg_x, " " * dlg_w,
                                  curses.color_pair(_CLR_DLG_INPUT))

            self._safe_addstr(stdscr, dlg_y, dlg_x,
                              "╭" + "─" * (dlg_w - 2) + "╮", curses.color_pair(_CLR_DLG_BORDER))
            for dy in range(1, dlg_h - 1):
                self._safe_addstr(stdscr, dlg_y + dy, dlg_x, "│", curses.color_pair(_CLR_DLG_BORDER))
                self._safe_addstr(stdscr, dlg_y + dy, dlg_x + dlg_w - 1, "│",
                                  curses.color_pair(_CLR_DLG_BORDER))
            self._safe_addstr(stdscr, dlg_y + dlg_h - 1, dlg_x,
                              "╰" + "─" * (dlg_w - 2) + "╯", curses.color_pair(_CLR_DLG_BORDER))

            self._safe_addstr(stdscr, dlg_y + 1, dlg_x + 2, f" {title} ",
                              curses.color_pair(_CLR_DLG_TITLE) | curses.A_BOLD)

            for i, line in enumerate(lines):
                if i >= dlg_h - 4:
                    break
                self._safe_addstr(stdscr, dlg_y + 3 + i, dlg_x + 2,
                                  f" {line}"[:dlg_w - 4], curses.color_pair(clr))

            self._safe_addstr(stdscr, dlg_y + dlg_h - 2, dlg_x + 2,
                              " 按任意键关闭", curses.color_pair(_CLR_DIM))

            stdscr.refresh()
            stdscr.nodelay(False)
            key = stdscr.getch()
            stdscr.nodelay(True)
            if key != -1:
                break

    def _dialog_help(self, stdscr: curses.window) -> None:
        """F1 / ? 帮助弹窗 — 显示全部快捷键和操作提示"""
        height, width = stdscr.getmaxyx()

        help_entries = [
            ("导航", [
                ("↑ ↓ / j k", "菜单上下移动"),
                ("PgUp / PgDn", "快速翻页"),
                ("Home / End", "跳到首/末项"),
                ("g / G", "跳到首/末项"),
            ]),
            ("操作", [
                ("Enter", "执行选中菜单项"),
                ("q", "退出 TUI"),
                ("s", "启动代理"),
                ("S", "停止代理"),
                ("r", "重启代理"),
                ("d", "后台运行模式"),
                ("h", "健康检查"),
                ("i", "运行状态"),
            ]),
            ("系统", [
                ("F5", "强制刷新状态 / 重测延迟"),
                ("F1 / ?", "打开此帮助面板"),
                ("Ctrl+E", "注册 systemd 开机自启"),
                ("Ctrl+U", "卸载 systemd 服务"),
                ("Esc", "关闭对话框 / 返回上级"),
            ]),
            ("表单编辑", [
                ("Enter", "编辑字段 / 确认修改"),
                ("S", "保存所有修改"),
                ("Esc", "放弃修改"),
                ("↑ ↓", "切换编辑字段"),
            ]),
        ]

        n_entries = sum(len(v) + 1 for _, v in help_entries)  # +1 for group header
        dlg_w = min(max(50, width - 8), 62)
        dlg_h = min(n_entries + 7, height - 4)
        dlg_x = (width - dlg_w) // 2
        dlg_y = (height - dlg_h) // 2

        # 完整绘制
        for dy in range(dlg_h):
            self._safe_addstr(stdscr, dlg_y + dy, dlg_x, " " * dlg_w,
                              curses.color_pair(_CLR_DLG_INPUT))
        self._draw_dlg_frame(stdscr, dlg_y, dlg_x, dlg_w, dlg_h, "快捷键帮助")

        row = dlg_y + 2
        for group_name, entries in help_entries:
            if row > dlg_y + dlg_h - 3:
                break
            # 分组标题
            header = f"  ◆ {group_name}"
            self._safe_addstr(stdscr, row, dlg_x + 2, header,
                              curses.color_pair(_CLR_TITLE) | curses.A_BOLD)
            row += 1
            for key_str, desc in entries:
                if row > dlg_y + dlg_h - 3:
                    break
                # 快捷键（左列）
                key_col = f"    {key_str}"
                self._safe_addstr(stdscr, row, dlg_x + 4, key_col,
                                  curses.color_pair(_CLR_VALUE) | curses.A_BOLD)
                # 说明（右列）
                gap = 16 - len(key_str)
                self._safe_addstr(stdscr, row, dlg_x + 4 + len(key_str) + max(gap, 1), desc,
                                  curses.color_pair(_CLR_HINT))
                row += 1

        # 底部提示
        bar_y = dlg_y + dlg_h - 2
        self._safe_addstr(stdscr, bar_y, dlg_x + 2, "按任意键关闭",
                          curses.color_pair(_CLR_KEYBAR))
        stdscr.refresh()

        stdscr.nodelay(False)
        stdscr.getch()
        stdscr.nodelay(True)
        self._dirty = True

    # ── 按键处理 ──

    def _handle_key(self, key: int, stdscr: curses.window) -> None:
        if key in (curses.KEY_UP, ord("k")):
            self.move_up()
        elif key in (curses.KEY_DOWN, ord("j")):
            self.move_down()
        elif key == curses.KEY_PPAGE:
            self.page_up()
        elif key == curses.KEY_NPAGE:
            self.page_down()
        elif key in (ord("\n"), curses.KEY_ENTER):
            action = self.get_selected_action()
            if not action:
                return
            self._execute_action(stdscr, action)
        elif key == ord("q"):
            self.quit()
        elif key == ord("s"):
            self._execute_action(stdscr, "start")
        elif key == ord("S"):
            self._execute_action(stdscr, "stop")
        elif key == ord("r"):
            self._execute_action(stdscr, "restart")
        elif key == ord("d"):
            self._execute_action(stdscr, "daemon")
        elif key == ord("h"):
            self._execute_action(stdscr, "health")
        elif key == ord("i"):
            self._execute_action(stdscr, "status")
        elif key == curses.KEY_F5:
            self._spawn_latency_check()
            self._config_cache_time = 0.0
            self._active_cache_time = 0.0
            self._dirty = True
        elif key == curses.KEY_F1 or key == ord("?"):
            self._dialog_help(stdscr)
        elif key == 5:  # Ctrl+E — 注册 systemd 开机自启
            self._execute_action(stdscr, "enable_svc")
        elif key == 21:  # Ctrl+U — 卸载 systemd 服务
            self._execute_action(stdscr, "disable_svc")

    def _execute_action(self, stdscr: curses.window, action: str) -> None:
        """执行操作：所有操作均在 TUI 内完成"""
        handler = getattr(self, f"_do_{action}", None)
        if handler:
            result = handler(stdscr)
            if result:
                self.message = result
                self.message_time = time.time()
            self._dirty = True

    def _save_config(self, config: dict[str, object]) -> str:
        try:
            bak = Path(str(CONFIG_PATH) + ".bak")
            if CONFIG_PATH.exists():
                try:
                    shutil.copy2(CONFIG_PATH, bak)
                except (OSError, PermissionError):
                    pass  # 备份非关键，静默跳过
            save_config(CONFIG_PATH, config)
            self._config_cache_time = 0.0
            return "配置已保存"
        except PermissionError:
            return "保存失败：需要 root 权限"
        except Exception as e:
            return f"保存失败：{e}"

    @staticmethod
    def _save_error_snapshot() -> None:
        """启动失败时保存 systemd 日志快照"""
        log_dir = Path.home() / ".autosocks"
        log_dir.mkdir(parents=True, exist_ok=True)
        error_file = log_dir / "error.log"
        try:
            result = subprocess.run(
                ["journalctl", "-u", "autosocks", "-n", "15", "--no-pager"],
                capture_output=True, text=True, timeout=10,
            )
            content = result.stdout.strip() or result.stderr.strip()
            if content:
                error_file.write_text(content)
        except Exception:
            error_file.write_text("(无法获取错误日志)")

    # ── 操作实现：代理管理 ──

    def _do_start(self, stdscr: curses.window) -> str:
        if os.geteuid() != 0:
            return "需要 root 权限，请使用 sudo autosocks tui"
        config = self._get_config()
        if not config.get("server_host"):
            return "未配置服务器地址，请先选择 [配置向导]"
        if service_is_active():
            return f"代理已在运行: {config['server_user']}@{config['server_host']}:{config['local_port']}"
        if service_start():
            self._active_cache_time = 0.0
            self._spawn_latency_check()
            return f"已启动: {config['server_user']}@{config['server_host']}:{config['local_port']}"
        # 启动失败 → 自动保存错误日志快照
        self._save_error_snapshot()
        return "启动失败，错误日志已保存至 ~/.autosocks/error.log"

    def _do_stop(self, stdscr: curses.window) -> str:
        if os.geteuid() != 0:
            return "需要 root 权限"
        if not service_is_active():
            return "代理未在运行"
        if service_stop():
            self._active_cache_time = 0.0
            self._latency = LatencyInfo()
            return "已停止"
        return "停止失败"

    def _do_restart(self, stdscr: curses.window) -> str:
        if os.geteuid() != 0:
            return "需要 root 权限"
        config = self._get_config()
        if service_restart():
            self._active_cache_time = 0.0
            self._spawn_latency_check()
            return f"已重启: {config.get('server_user', 'root')}@{config.get('server_host', '')}"
        return "重启失败"

    def _do_status(self, stdscr: curses.window) -> str:
        config = self._get_config()
        server = f"{config.get('server_user', 'root')}@{config.get('server_host', '未配置')}"
        port = str(config.get('local_port', 1080))
        bind = str(config.get('local_bind', '127.0.0.1'))
        active = self._get_active()
        status = "运行中" if active else "未运行"
        lines = [f"状态: {status}", f"服务器: {server}", f"端口: {port}", f"绑定: {bind}"]
        latency = self._get_latency()
        if latency.ms >= 0:
            lines.append(f"延迟: {latency.ms:.0f}ms")
        if latency.exit_ip:
            lines.append(f"出口 IP: {latency.exit_ip}")
        self._dialog_message(stdscr, "运行状态", lines)
        return ""

    def _do_health(self, stdscr: curses.window) -> str:
        from autosocks.plugins.health import check_health
        active = self._get_active()
        if not active:
            return "服务未运行，无法检查"
        config = self._get_config()
        port = int(str(config.get('local_port', 1080)))
        result = check_health(port)
        lines = [
            f"服务状态: {'运行中' if result.service_active else '未运行'}",
            f"代理可用: {'是' if result.proxy_ok else '否'}",
        ]
        if result.exit_ip:
            lines.append(f"出口 IP: {result.exit_ip}")
        lines.append(f"健康状态: {result.status.value}")
        self._dialog_message(stdscr, "健康检查", lines, _CLR_SUCCESS if result.proxy_ok else _CLR_ERROR)
        return ""

    def _do_latency_test(self, stdscr: curses.window) -> str:
        if not self._get_active():
            return "服务未运行，无法测试延迟"
        self._latency = LatencyInfo()
        self._spawn_latency_check()
        return "延迟测试已启动，请稍后查看状态面板"

    # ── 操作实现：代理工具 ──

    def _do_http_proxy(self, stdscr: curses.window) -> str:
        from autosocks.plugins.proxy import start_http_proxy, detect_gost
        if not self._get_active():
            return "代理服务未运行，请先启动"
        gost = detect_gost()
        if not gost:
            return "未检测到 gost，请先安装\n  https://github.com/ginuerzh/gost"
        config = self._get_config()
        socks_port = int(str(config.get('local_port', 1080)))
        http_port = socks_port + 1
        if start_http_proxy(socks_port, http_port):
            return f"HTTP 代理已启动: 127.0.0.1:{http_port}\nSOCKS5 → HTTP 转发中"
        return "启动失败"

    def _do_env(self, stdscr: curses.window) -> str:
        """环境变量管理 — 在 TUI 内安装/卸载代理环境变量"""
        config = self._get_config()
        bind = str(config.get('local_bind', '127.0.0.1'))
        port = int(str(config.get('local_port', 1080)))
        proxy_url = f"socks5h://{bind}:{port}"
        active = self._get_active()

        height, width = stdscr.getmaxyx()
        dlg_w = min(58, width - 4)
        dlg_h = min(22, height - 4)
        dlg_x = (width - dlg_w) // 2
        dlg_y = (height - dlg_h) // 2

        # 默认选中项
        defaults = {
            "http_proxy": True, "https_proxy": True, "HTTP_PROXY": True, "HTTPS_PROXY": True,
            "all_proxy": True, "ALL_PROXY": True, "no_proxy": True, "NO_PROXY": True,
            "socks_proxy": True, "SOCKS_PROXY": True, "ftp_proxy": True, "FTP_PROXY": True,
        }
        no_proxy_hosts = "localhost,127.0.0.1,::1"
        script_path = Path.home() / ".autosocks.sh"
        integration_installed = script_path.exists()
        selected_row = 0

        # 可滚动的勾选项列表
        checkbox_items = list(defaults.keys())
        n_checkboxes = len(checkbox_items)

        def _draw_panel(keys_hint: str = "") -> None:
            # 清空面板区域
            for dy in range(dlg_h):
                self._safe_addstr(stdscr, dlg_y + dy, dlg_x, " " * dlg_w,
                                  curses.color_pair(_CLR_DLG_INPUT))
            self._draw_dlg_frame(stdscr, dlg_y, dlg_x, dlg_w, dlg_h, "环境变量管理")

            row = dlg_y + 2
            # 服务状态
            svc_status = "● 代理运行中" if active else "○ 代理未启动"
            svc_clr = _CLR_RUNNING if active else _CLR_STOPPED
            self._safe_addstr(stdscr, row, dlg_x + 2, "状态:  ", curses.color_pair(_CLR_HINT))
            self._safe_addstr(stdscr, row, dlg_x + 8, svc_status, curses.color_pair(svc_clr) | curses.A_BOLD)
            row += 1

            # 代理地址
            self._safe_addstr(stdscr, row, dlg_x + 2, f"地址:  {proxy_url}",
                              curses.color_pair(_CLR_VALUE) | curses.A_BOLD)
            row += 1

            # 分隔线
            self._safe_addstr(stdscr, row, dlg_x + 3, "─" * (dlg_w - 8),
                              curses.color_pair(_CLR_BORDER))
            row += 1

            # 勾选项（支持滚动）
            visible_start = max(0, selected_row - (dlg_h - row - 7))
            visible_end = min(n_checkboxes, visible_start + (dlg_h - row - 7))
            for idx in range(visible_start, visible_end):
                k = checkbox_items[idx]
                checked = defaults[k]
                cursor = "▸" if idx == selected_row else " "
                mark = "✓" if checked else " "
                self._safe_addstr(stdscr, row, dlg_x + 3, f"{cursor}",
                                  curses.color_pair(_CLR_TITLE) | curses.A_BOLD)
                self._safe_addstr(stdscr, row, dlg_x + 5, f"[{mark}]",
                                  curses.color_pair(_CLR_SUCCESS if checked else _CLR_DIM) | curses.A_BOLD)
                self._safe_addstr(stdscr, row, dlg_x + 9, f"{k}={proxy_url}",
                                  curses.color_pair(_CLR_VALUE))
                row += 1

            # 留空一行
            row += 1

            # no_proxy 自定义
            self._safe_addstr(stdscr, row, dlg_x + 2, "no_proxy 忽略:",
                              curses.color_pair(_CLR_HINT))
            self._safe_addstr(stdscr, row, dlg_x + 18, no_proxy_hosts,
                              curses.color_pair(_CLR_VALUE) | curses.A_BOLD)
            row += 1

            # Shell 集成状态
            int_status = "已安装 ✓" if integration_installed else "未安装"
            self._safe_addstr(stdscr, row, dlg_x + 2, f"Shell 集成: {int_status}",
                              curses.color_pair(_CLR_HINT))
            row += 1

            # 底部按键栏
            bar_y = dlg_y + dlg_h - 2
            keys = "  ←/→/↑/↓ 移动    Space 切换    E 安装    U 卸载    Esc 关闭"
            if keys_hint:
                keys = keys_hint
            self._safe_addstr(stdscr, bar_y, dlg_x + 2, keys[:dlg_w - 4],
                              curses.color_pair(_CLR_KEYBAR))

        stdscr.nodelay(False)
        result: str | None = None
        scroll_offset = 0
        while True:
            _draw_panel()
            stdscr.refresh()
            key = stdscr.getch()

            if key == 27:  # Esc
                result = "已关闭"
                break
            elif key == ord("q"):
                result = "已关闭"
                break
            elif key in (curses.KEY_UP, ord("k")):
                if selected_row > 0:
                    selected_row -= 1
                elif scroll_offset > 0:
                    scroll_offset -= 1
                    selected_row = scroll_offset
            elif key in (curses.KEY_DOWN, ord("j")):
                if selected_row < n_checkboxes - 1:
                    selected_row += 1
                elif scroll_offset < n_checkboxes - (dlg_h - dlg_y - 8):
                    scroll_offset += 1
                    selected_row = scroll_offset + (dlg_h - dlg_y - 8) - 1
            elif key == ord(" "):  # 切换选中
                k = checkbox_items[selected_row]
                defaults[k] = not defaults[k]
            elif key in (ord("e"), ord("E")):  # 安装
                result = self._env_install(defaults, no_proxy_hosts, bind, port, script_path)
                break
            elif key in (ord("u"), ord("U")):  # 卸载
                result = self._env_uninstall(script_path)
                break
            elif key == curses.KEY_RESIZE:
                height, width = stdscr.getmaxyx()
                dlg_w = min(58, width - 4)
                dlg_h = min(22, height - 4)
                dlg_x = (width - dlg_w) // 2
                dlg_y = (height - dlg_h) // 2

        stdscr.nodelay(True)
        self._dirty = True
        return result or "已关闭"

    def _env_install(self, toggles: dict[str, bool], no_proxy_hosts: str,
                     bind: str, port: int, script_path: Path) -> str:
        """生成并安装 Shell 环境变量脚本"""
        proxy_url = f"socks5h://{bind}:{port}"
        lines: list[str] = ["# AutoSOCKS 代理环境变量 (TUI 管理)", ""]
        for var, enabled in toggles.items():
            if enabled:
                if var in ("no_proxy", "NO_PROXY"):
                    lines.append(f'export {var}="{no_proxy_hosts}"')
                else:
                    lines.append(f'export {var}="{proxy_url}"')
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("\n".join(lines) + "\n")
        # 添加到 bashrc（若未添加）
        bashrc = Path.home() / ".bashrc"
        source_line = f'source "{script_path}" 2>/dev/null'
        if bashrc.exists() and source_line not in bashrc.read_text():
            with bashrc.open("a") as f:
                f.write(f"\n# AutoSOCKS\n{source_line}\n")
        return "Shell 集成已安装\n可执行 source ~/.autosocks.sh 立即生效"

    def _env_uninstall(self, script_path: Path) -> str:
        """卸载 Shell 环境变量脚本"""
        if script_path.exists():
            script_path.unlink()
        bashrc = Path.home() / ".bashrc"
        if bashrc.exists():
            content = bashrc.read_text()
            if "AutoSOCKS" in content:
                new_content = "\n".join(
                    line for line in content.split("\n")
                    if 'AutoSOCKS' not in line and '.autosocks.sh' not in line
                )
                bashrc.write_text(new_content)
        return "Shell 集成已卸载"

    def _do_shell_integration(self, stdscr: curses.window) -> str:
        """Shell 集成 — 快速安装/卸载代理环境变量"""
        script_path = Path.home() / ".autosocks.sh"
        installed = script_path.exists()
        idx = self._dialog_select(stdscr, "Shell 集成",
                                  ["安装环境变量", "卸载环境变量"], 0 if not installed else 1)
        if idx is None or idx < 0:
            return ""
        config = self._get_config()
        bind = str(config.get('local_bind', '127.0.0.1'))
        port = int(str(config.get('local_port', 1080)))
        toggles = {
            "http_proxy": True, "https_proxy": True, "HTTP_PROXY": True, "HTTPS_PROXY": True,
            "all_proxy": True, "ALL_PROXY": True, "no_proxy": True, "NO_PROXY": True,
            "socks_proxy": True, "SOCKS_PROXY": True, "ftp_proxy": True, "FTP_PROXY": True,
        }
        if idx == 0:
            return self._env_install(toggles, "localhost,127.0.0.1,::1", bind, port, script_path)
        else:
            return self._env_uninstall(script_path)

    # ── 操作实现：配置编辑 ──

    def _do_install(self, stdscr: curses.window) -> str:
        """交互式配置向导"""
        if os.geteuid() != 0:
            return "需要 root 权限"

        server_input = self._dialog_input(stdscr, "服务器地址（user@host[:port]）")
        if server_input is None:
            return "已取消"
        if not server_input:
            return "已取消"

        if "@" in server_input:
            user, host_part = server_input.split("@", 1)
        else:
            user = "root"
            host_part = server_input

        server_port = 22
        if ":" in host_part and not host_part.startswith("["):
            host, port_str = host_part.rsplit(":", 1)
            server_port = int(port_str) if port_str.isdigit() else 22
        elif host_part.startswith("["):
            bracket_end = host_part.find("]")
            if bracket_end == -1:
                host = host_part
            else:
                host = host_part[1:bracket_end]
                rest = host_part[bracket_end + 1:]
                if rest.startswith(":"):
                    server_port = int(rest[1:]) if rest[1:].isdigit() else 22
        else:
            host = host_part

        if not host.strip():
            return "服务器地址不能为空"

        local_port_str = self._dialog_input(stdscr, "本地 SOCKS5 端口", "1080")
        if local_port_str is None:
            return "已取消"
        local_port = int(local_port_str) if local_port_str and local_port_str.isdigit() else 1080

        bind = self._dialog_input(stdscr, "绑定地址", "127.0.0.1")
        if bind is None:
            return "已取消"
        bind = bind or "127.0.0.1"

        auth_idx = self._dialog_select(stdscr, "认证方式", ["SSH 密钥", "密码认证"], 0)
        if auth_idx is None:
            return "已取消"
        auth_type = "key" if auth_idx == 0 else "password"

        key_path = ""
        auth_password = ""
        if auth_type == "key":
            key_path_result = self._dialog_input(stdscr, "SSH 密钥路径", "~/.ssh/id_rsa")
            if key_path_result is None:
                return "已取消"
            key_path = key_path_result
        else:
            pwd_result = self._dialog_input(stdscr, "SSH 密码")
            if pwd_result is None:
                return "已取消"
            auth_password = pwd_result

        keepalive_result = self._dialog_input(stdscr, "心跳间隔（秒）", "60")
        keepalive = keepalive_result if keepalive_result else "60"
        timeout_result = self._dialog_input(stdscr, "连接超时（秒）", "10")
        timeout = timeout_result if timeout_result else "10"

        recon_idx = self._dialog_select(stdscr, "自动重连", ["开启", "关闭"], 0)
        if recon_idx is None:
            return "已取消"
        recon_int_result = self._dialog_input(stdscr, "重连间隔（秒）", "3")
        recon_int = recon_int_result if recon_int_result else "3"

        log_idx = self._dialog_select(stdscr, "日志", ["开启", "关闭"], 0)
        if log_idx is None:
            return "已取消"

        # 预览确认
        preview_lines = [
            f"  服务器: {user}@{host}:{server_port}",
            f"  本地端口: {bind}:{local_port}",
            f"  认证: {auth_type}" + (f" ({key_path})" if key_path else ""),
            f"  心跳: {keepalive}s  超时: {timeout}s",
            f"  重连: {'开' if recon_idx == 0 else '关'}  间隔: {recon_int}s",
            f"  日志: {'开' if log_idx == 0 else '关'}",
        ]
        self._dialog_message(stdscr, "配置预览", preview_lines)

        confirm = self._dialog_select(stdscr, "确认保存？", ["是，保存配置", "否，取消"], 0)
        if confirm is None or confirm != 0:
            return "已取消"

        config = {
            "server_host": host,
            "server_user": user,
            "server_port": server_port,
            "local_port": local_port,
            "local_bind": bind,
            "auth_type": auth_type,
            "auth_key_path": key_path,
            "auth_password": auth_password,
            "ssh_keepalive": int(keepalive) if keepalive.isdigit() else 60,
            "ssh_timeout": int(timeout) if timeout.isdigit() else 10,
            "reconnect_enabled": recon_idx == 0,
            "reconnect_interval": int(recon_int) if recon_int.isdigit() else 3,
            "log_enabled": log_idx == 0,
        }
        save_config(CONFIG_PATH, config)
        self._config_cache_time = 0.0
        return f"配置已保存: {user}@{host}:{server_port}"

    def _do_setup_wizard(self, stdscr: curses.window) -> str:
        """快速上手引导 - 逐步引导用户完成所有核心配置"""
        if os.geteuid() != 0:
            return "需要 root 权限，请使用 sudo autosocks tui"

        config = dict(self._get_config())

        # ── 第 1 步：欢迎 ──
        self._dialog_message(stdscr, "🚀 欢迎使用 AutoSOCKS", [
            "本向导将逐步引导您完成",
            "SOCKS5 代理服务的配置",
            "",
            "全程约需 2 分钟",
            "按任意键开始...",
        ])

        # ── 第 2 步：服务器 ──
        server_result = self._dialog_input(
            stdscr, "第 1 步：远程服务器地址",
            f"{config.get('server_user', 'root')}@{config.get('server_host', '')}"
        )
        if server_result is None:
            return "引导已取消"
        if not server_result:
            return "引导已取消：服务器地址不能为空"

        if "@" in server_result:
            user, host_part = server_result.split("@", 1)
        else:
            user = "root"
            host_part = server_result

        server_port = 22
        host = host_part
        if ":" in host_part and not host_part.startswith("["):
            host, port_str = host_part.rsplit(":", 1)
            server_port = int(port_str) if port_str.isdigit() else 22
        elif host_part.startswith("["):
            bracket_end = host_part.find("]")
            if bracket_end >= 0:
                host = host_part[1:bracket_end]
                rest = host_part[bracket_end + 1:]
                if rest.startswith(":"):
                    server_port = int(rest[1:]) if rest[1:].isdigit() else 22

        config["server_host"] = host
        config["server_user"] = user
        config["server_port"] = server_port

        # ── 第 3 步：本地端口 ──
        local_port_result = self._dialog_input(
            stdscr, "第 2 步：本地 SOCKS5 端口",
            str(config.get("local_port", 1080))
        )
        if local_port_result is None:
            return "引导已取消"
        if local_port_result and local_port_result.isdigit():
            config["local_port"] = int(local_port_result)

        bind_result = self._dialog_input(
            stdscr, "绑定地址（默认 127.0.0.1 仅本机可用）",
            str(config.get("local_bind", "127.0.0.1"))
        )
        if bind_result:
            config["local_bind"] = bind_result

        # ── 第 4 步：认证 ──
        auth_idx = self._dialog_select(stdscr, "第 3 步：SSH 认证方式", [
            "SSH 密钥认证（推荐）",
            "密码认证"
        ], 0 if str(config.get("auth_type")) == "key" else 1)
        if auth_idx is None:
            return "引导已取消"

        config["auth_type"] = "key" if auth_idx == 0 else "password"
        if auth_idx == 0:
            key_result = self._dialog_input(
                stdscr, "SSH 密钥路径",
                str(config.get("auth_key_path", "~/.ssh/id_rsa"))
            )
            if key_result is not None:
                config["auth_key_path"] = key_result
        else:
            pwd_result = self._dialog_input(stdscr, "SSH 登录密码")
            if pwd_result is not None:
                config["auth_password"] = pwd_result

        # ── 第 5 步：高级选项 ──
        self._dialog_message(stdscr, "高级设置", [
            "以下为可选的 SSH 参数",
            "如不确定，直接回车使用默认值即可",
        ])

        keepalive_result = self._dialog_input(
            stdscr, "心跳间隔（秒）", str(config.get("ssh_keepalive", 60))
        )
        if keepalive_result and keepalive_result.isdigit():
            config["ssh_keepalive"] = int(keepalive_result)

        timeout_result = self._dialog_input(
            stdscr, "连接超时（秒）", str(config.get("ssh_timeout", 10))
        )
        if timeout_result and timeout_result.isdigit():
            config["ssh_timeout"] = int(timeout_result)

        recon_idx = self._dialog_select(stdscr, "自动重连", [
            "开启（推荐）", "关闭"
        ], 0 if config.get("reconnect_enabled", True) else 1)
        if recon_idx is not None:
            config["reconnect_enabled"] = recon_idx == 0

        log_idx = self._dialog_select(stdscr, "日志记录", [
            "开启（推荐）", "关闭"
        ], 0 if config.get("log_enabled", True) else 1)
        if log_idx is not None:
            config["log_enabled"] = log_idx == 0

        # ── 第 6 步：预览确认 ──
        auth_display = "SSH 密钥" if config["auth_type"] == "key" else "密码认证"
        preview_lines = [
            "── 配置摘要 ──",
            "",
            f"  服务器: {user}@{host}:{server_port}",
            f"  本地监听: {config['local_bind']}:{config['local_port']}",
            f"  认证方式: {auth_display}",
            f"  心跳间隔: {config['ssh_keepalive']}s",
            f"  连接超时: {config['ssh_timeout']}s",
            f"  自动重连: {'开' if config.get('reconnect_enabled', True) else '关'}",
            f"  日志记录: {'开' if config.get('log_enabled', True) else '关'}",
            "",
            "确认后将保存配置并准备启动",
        ]
        self._dialog_message(stdscr, "配置确认", preview_lines)

        confirm = self._dialog_select(stdscr, "确认保存配置？", [
            "是，保存并启动代理",
            "是，仅保存配置",
            "否，取消"
        ], 0)
        if confirm is None or confirm == 2:
            return "引导已取消"

        save_config(CONFIG_PATH, config)
        self._config_cache_time = 0.0

        if confirm == 0:
            # 保存配置后尝试启动
            if service_start():
                self._active_cache_time = 0.0
                self._spawn_latency_check()
                self._dialog_message(stdscr, "配置完成", [
                    "配置已保存并成功启动代理！",
                    "",
                    f"SOCKS5 代理: {config['local_bind']}:{config['local_port']}",
                    "",
                    "使用命令管理:",
                    "  autosocks status  查看状态",
                    "  autosocks stop    停止代理",
                    "  autosocks tui     管理界面",
                ], _CLR_SUCCESS)
                return f"配置完成并已启动: {user}@{host}:{server_port}"
            else:
                self._dialog_message(stdscr, "启动失败", [
                    "配置已保存，但启动失败",
                    "请检查服务器连接和认证设置",
                    "",
                    f"服务器: {user}@{host}:{server_port}",
                    f"认证: {auth_display}",
                ], _CLR_ERROR)
                return "配置已保存，但启动失败"
        else:
            return f"配置已保存: {user}@{host}:{server_port}"

    def _do_edit_server(self, stdscr: curses.window) -> str:
        """编辑服务器设置 - 使用统一表单"""
        config = dict(self._get_config())
        result = self._dialog_form(stdscr, "服务器设置", [
            ("server_host", "服务器地址",  config.get("server_host", ""),   "text",   None),
            ("server_user", "SSH 用户名",  config.get("server_user", "root"), "text",  None),
            ("server_port", "SSH 端口",    config.get("server_port", 22),   "number", None),
        ], ["格式: host[:port] 或 user@host[:port]"])
        if result is None:
            return "已取消"
        config.update(result)
        return self._save_config(config)

    def _do_edit_local(self, stdscr: curses.window) -> str:
        """编辑本地端口设置 - 使用统一表单"""
        config = dict(self._get_config())
        result = self._dialog_form(stdscr, "本地端口设置", [
            ("local_bind", "绑定地址",     config.get("local_bind", "127.0.0.1"), "text",   None),
            ("local_port", "SOCKS5 端口",  config.get("local_port", 1080),        "number", None),
        ], ["127.0.0.1 = 仅本机可用", "0.0.0.0 = 所有网络可用"])
        if result is None:
            return "已取消"
        config.update(result)
        return self._save_config(config)

    def _do_edit_auth(self, stdscr: curses.window) -> str:
        """编辑认证设置 - 使用统一表单"""
        config = dict(self._get_config())
        auth_is_key = str(config.get("auth_type", "key")) == "key"
        result = self._dialog_form(stdscr, "认证设置", [
            ("auth_type",    "认证方式",    0 if auth_is_key else 1,      "select",   ["SSH 密钥认证", "密码认证"]),
            ("auth_key_path","密钥路径",    config.get("auth_key_path", "~/.ssh/id_rsa"), "text", None),
            ("auth_password","SSH 密码",    config.get("auth_password", ""), "password", None),
        ], ["密钥认证推荐，更安全"])
        if result is None:
            return "已取消"
        auth_type_idx = result.pop("auth_type", 0 if auth_is_key else 1)
        result["auth_type"] = "key" if auth_type_idx == 0 else "password"
        config.update(result)
        return self._save_config(config)

    def _do_edit_ssh(self, stdscr: curses.window) -> str:
        """编辑 SSH 参数 - 使用统一表单"""
        config = dict(self._get_config())
        result = self._dialog_form(stdscr, "SSH 参数设置", [
            ("ssh_keepalive", "心跳间隔 (秒)", config.get("ssh_keepalive", 60),  "number", None),
            ("ssh_timeout",   "连接超时 (秒)", config.get("ssh_timeout", 10),    "number", None),
        ], ["心跳保持长连接不中断", "超时过短可能导致连接失败"])
        if result is None:
            return "已取消"
        config.update(result)
        return self._save_config(config)

    def _do_edit_reconnect(self, stdscr: curses.window) -> str:
        """编辑重连设置 - 使用统一表单"""
        config = dict(self._get_config())
        result = self._dialog_form(stdscr, "重连设置", [
            ("reconnect_enabled",  "自动重连",    config.get("reconnect_enabled", True), "bool", None),
            ("reconnect_interval", "重连间隔 (秒)", config.get("reconnect_interval", 3), "number", None),
        ], ["断线后自动重连，推荐开启"])
        if result is None:
            return "已取消"
        config.update(result)
        return self._save_config(config)

    def _do_edit_log(self, stdscr: curses.window) -> str:
        """编辑日志设置 - 使用统一表单"""
        config = dict(self._get_config())
        result = self._dialog_form(stdscr, "日志设置", [
            ("log_enabled",  "启用日志",         config.get("log_enabled", True),  "bool", None),
            ("log_max_size", "最大大小 (字节)",    config.get("log_max_size", 1048576), "number", None),
        ], ["日志文件路径: /var/log/autosocks.log"])
        if result is None:
            return "已取消"
        config.update(result)
        return self._save_config(config)

    def _do_edit_webhook(self, stdscr: curses.window) -> str:
        """编辑 Webhook 告警设置"""
        config = dict(self._get_config())
        result = self._dialog_form(stdscr, "Webhook 告警", [
            ("webhook_url", "回调 URL", config.get("webhook_url", ""), "text", None),
        ], ["服务异常时推送告警通知"])
        if result is None:
            return "已取消"
        config.update(result)
        url = str(config.get("webhook_url", ""))
        if url:
            idx = self._dialog_select(stdscr, "发送测试", ["是，发送测试消息", "否，仅保存"], 1)
            if idx == 0:
                from autosocks.plugins.webhook import send_webhook
                if send_webhook(url, f"AutoSOCKS v{__version__} Webhook 测试"):
                    self._dialog_message(stdscr, "Webhook", ["测试消息发送成功"], _CLR_SUCCESS)
                else:
                    self._dialog_message(stdscr, "Webhook", ["测试消息发送失败，请检查 URL"], _CLR_ERROR)
        return self._save_config(config)

    def _do_edit_geo(self, stdscr: curses.window) -> str:
        """编辑 GeoIP 分流设置"""
        config = dict(self._get_config())
        e = config.get("geo_enabled", False)
        result = self._dialog_form(stdscr, "GeoIP 分流", [
            ("geo_enabled", "启用分流",   e,                       "bool", None),
            ("geo_ip_list", "IP 列表路径", config.get("geo_ip_list", "/etc/autosocks/china_ip_list.txt"), "text", None),
        ], ["国内 IP 走直连，国外走代理"])
        if result is None:
            return "已取消"
        config.update(result)
        if config.get("geo_enabled", False):
            update_choice = self._dialog_select(stdscr, "更新 IP 列表", ["是，立即更新", "否"], 1)
            if update_choice == 0:
                from autosocks.plugins.geo import update_ip_list
                list_path = Path(str(config.get("geo_ip_list", "/etc/autosocks/china_ip_list.txt")))
                if update_ip_list(list_path):
                    self._dialog_message(stdscr, "GeoIP", ["IP 列表更新成功"], _CLR_SUCCESS)
                else:
                    self._dialog_message(stdscr, "GeoIP", ["IP 列表更新失败，请检查网络"], _CLR_ERROR)
        return self._save_config(config)

    # ── 操作实现：Profile 管理 ──

    @staticmethod
    def _sanitize_profile_name(name: str) -> str | None:
        """校验 profile 名称，防止路径遍历。合法返回名称，非法返回 None。"""
        if not name:
            return None
        if not re.match(r'^[a-zA-Z0-9._-]+$', name):
            return None
        if name.startswith('.') or '..' in name:
            return None
        return name

    def _do_profile_list(self, stdscr: curses.window) -> str:
        """列出所有 Profile"""
        from autosocks.plugins.profile import list_profiles
        profiles = list_profiles(PROFILE_DIR)
        if not profiles:
            self._dialog_message(stdscr, "Profiles", ["暂无 Profile", "可通过 [创建 Profile] 添加"])
            return ""

        config = self._get_config()
        current = f"{config.get('server_user', 'root')}@{config.get('server_host', '未配置')}"

        lines = [f"当前配置: {current}", ""]
        for name in profiles:
            if self._sanitize_profile_name(name) is None:
                continue
            p_path = PROFILE_DIR / f"{name}.conf"
            p_config = load_config(p_path)
            p_info = (f"{p_config.get('server_user', 'root')}@"
                      f"{p_config.get('server_host', '?')}:{p_config.get('local_port', 1080)}")
            lines.append(f"  {name}: {p_info}")
        self._dialog_message(stdscr, "Profiles", lines)
        return ""

    def _do_profile_create(self, stdscr: curses.window) -> str:
        """创建新 Profile"""
        if os.geteuid() != 0:
            return "需要 root 权限"

        name = self._dialog_input(stdscr, "Profile 名称")
        if name is None or not name:
            return "已取消"
        safe_name = self._sanitize_profile_name(name)
        if safe_name is None:
            return "Profile 名称无效，只允许字母、数字、连字符、下划线和点"

        config = dict(self._get_config())
        confirm = self._dialog_select(stdscr, f"创建 Profile '{safe_name}'？",
                                      ["基于当前配置创建", "取消"], 0)
        if confirm is None or confirm != 0:
            return "已取消"

        from autosocks.plugins.profile import create_profile
        p_path = PROFILE_DIR / f"{safe_name}.conf"
        if create_profile(p_path, config):
            return f"Profile '{safe_name}' 已创建"
        return "创建失败"

    def _do_profile_switch(self, stdscr: curses.window) -> str:
        """切换 Profile"""
        from autosocks.plugins.profile import list_profiles
        profiles = list_profiles(PROFILE_DIR)
        if not profiles:
            return "暂无 Profile，请先创建"

        # 构建带信息的选项列表
        options = []
        for name in profiles:
            p_path = PROFILE_DIR / f"{name}.conf"
            p_config = load_config(p_path)
            p_info = f"{p_config.get('server_user', 'root')}@{p_config.get('server_host', '?')}"
            options.append(f"{name} ({p_info})")

        idx = self._dialog_select(stdscr, "切换 Profile", options, 0)
        if idx is None:
            return "已取消"

        selected_name = profiles[idx]
        p_path = PROFILE_DIR / f"{selected_name}.conf"
        p_config = load_config(p_path)

        save_config(CONFIG_PATH, p_config)
        self._config_cache_time = 0.0

        if self._get_active():
            restart = self._dialog_select(stdscr, "服务正在运行，是否重启以应用新配置？",
                                          ["是，重启", "否，稍后手动重启"], 0)
            if restart == 0:
                service_restart()
                self._active_cache_time = 0.0

        return f"已切换到 Profile '{selected_name}'"

    def _do_profile_delete(self, stdscr: curses.window) -> str:
        """删除 Profile"""
        from autosocks.plugins.profile import list_profiles, delete_profile
        profiles = list_profiles(PROFILE_DIR)
        if not profiles:
            return "暂无 Profile"

        idx = self._dialog_select(stdscr, "选择要删除的 Profile", profiles, 0)
        if idx is None:
            return "已取消"

        selected_name = profiles[idx]
        confirm = self._dialog_select(stdscr, f"确认删除 Profile '{selected_name}'？",
                                      ["是，删除", "否，取消"], 1)
        if confirm is None or confirm != 0:
            return "已取消"

        p_path = PROFILE_DIR / f"{selected_name}.conf"
        if delete_profile(p_path):
            return f"Profile '{selected_name}' 已删除"
        return "删除失败"

    # ── 操作实现：系统工具 ──

    def _do_update(self, stdscr: curses.window) -> str:
        from autosocks.plugins.update import check_latest_version, perform_update
        from autosocks import __version__ as current

        latest = check_latest_version()
        if latest is None:
            return "无法检查更新（网络错误）"
        if latest == current:
            return f"已是最新版本: v{current}"

        msg_lines = [f"发现新版本: v{latest}（当前 v{current}）"]
        if perform_update():
            msg_lines.append("更新成功！请重启 autosocks")
            self._dialog_message(stdscr, "更新", msg_lines, _CLR_SUCCESS)
        else:
            msg_lines.append("更新失败，请手动运行:")
            msg_lines.append("  sudo pip install --upgrade autosocks")
            self._dialog_message(stdscr, "更新", msg_lines, _CLR_ERROR)
        return ""

    def _do_view_config(self, stdscr: curses.window) -> str:
        """查看完整配置"""
        config = self._get_config()
        lines = ["── 完整配置 ──", ""]
        for key, value in sorted(config.items()):
            lines.append(f"  {key} = {value}")
        lines.append("")
        lines.append(f"配置文件: {CONFIG_PATH}")
        self._dialog_message(stdscr, "完整配置", lines)
        return ""

    def _do_view_log(self, stdscr: curses.window) -> str:
        """查看日志"""
        log_lines: list[str] = []

        # 尝试 journalctl
        try:
            result = subprocess.run(
                ["journalctl", "-u", "autosocks", "-n", "20", "--no-pager"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                log_lines.extend(result.stdout.strip().split("\n")[-20:])
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 也检查日志文件
        log_path = Path("/var/log/autosocks.log")
        if log_path.exists():
            try:
                with open(log_path) as f:
                    tail = deque(f, maxlen=20)
                if log_lines:
                    log_lines.append("── 日志文件 ──")
                log_lines.extend(line.rstrip() for line in tail)
            except PermissionError:
                log_lines.append(f"无权限读取 {log_path}")

        if not log_lines:
            log_lines = ["暂无日志"]

        self._dialog_message(stdscr, "日志", log_lines)
        return ""

    def _do_daemon(self, stdscr: curses.window) -> str:
        """后台运行模式 - TUI 关闭但服务继续运行"""
        active = self._get_active()
        if not active:
            return "服务未运行，无法切换到后台\n请先启动代理"

        config = self._get_config()
        server = f"{config.get('server_user', 'root')}@{config.get('server_host', '未配置')}"
        port = config.get('local_port', 1080)
        bind = str(config.get('local_bind', '127.0.0.1'))

        # 显示确认信息
        self._dialog_message(stdscr, "切换到后台运行", [
            "TUI 界面即将关闭",
            "代理服务将在后台持续运行",
            "",
            f"服务器: {server}",
            f"代理地址: socks5://{bind}:{port}",
            "",
            "管理命令:",
            "  autosocks status  查看状态",
            "  autosocks stop    停止代理",
            "  autosocks tui     重新打开界面",
        ], _CLR_SUCCESS)

        self.quit()
        return (
            f"代理服务已在后台运行\n"
            f"  服务器: {server}\n"
            f"  端口: {port}\n\n"
            f"管理命令:\n"
            f"  autosocks status  查看状态\n"
            f"  autosocks stop    停止代理\n"
            f"  autosocks tui     重新打开 TUI"
        )

    def _do_quit(self, stdscr: curses.window) -> str:
        self.quit()
        return ""

    def _do_enable_svc(self, stdscr: curses.window) -> str:
        """Ctrl+E — 注册 systemd 开机自启"""
        if os.geteuid() != 0:
            return "需要 root 权限"
        result = subprocess.run(
            ["systemctl", "enable", "autosocks"],
            capture_output=True, text=True,
        )
        return "已注册开机自启" if result.returncode == 0 else f"注册失败: {result.stderr.strip()}"

    def _do_disable_svc(self, stdscr: curses.window) -> str:
        """Ctrl+U — 卸载 systemd 服务（需确认）"""
        if os.geteuid() != 0:
            return "需要 root 权限"
        choice = self._dialog_select(stdscr, "确认卸载 systemd 服务？", ["取消", "确认卸载"], 0)
        if choice != 1:
            return "已取消"
        for cmd in [["systemctl", "stop", "autosocks"],
                     ["systemctl", "disable", "autosocks"]]:
            subprocess.run(cmd, capture_output=True)
        return "服务已停止并取消自启"
