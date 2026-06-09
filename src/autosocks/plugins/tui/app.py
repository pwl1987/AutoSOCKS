"""TUI L3 全屏交互界面 - curses 主界面"""
from __future__ import annotations

import curses
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from autosocks import __version__
from autosocks.core.config import load_config
from autosocks.core.service import service_start, service_stop, service_restart, service_is_active


CONFIG_PATH = Path("/etc/autosocks/config.conf")


@dataclass
class MenuItem:
    """菜单项"""
    label: str
    action: str


class TUIApp:
    """curses 全屏 TUI 应用"""

    def __init__(self) -> None:
        self.items = self.default_menu_items()
        self.selected = 0
        self.running = True
        self.message = ""
        self._actions: dict[str, Callable[[], str]] = {
            "start": self._do_start,
            "stop": self._do_stop,
            "restart": self._do_restart,
            "status": self._do_status,
            "install": self._do_install,
            "quit": self._do_quit,
        }

    @staticmethod
    def default_menu_items() -> list[MenuItem]:
        """默认菜单项"""
        return [
            MenuItem("启动代理", "start"),
            MenuItem("停止代理", "stop"),
            MenuItem("重启代理", "restart"),
            MenuItem("查看状态", "status"),
            MenuItem("配置服务器", "install"),
            MenuItem("退出", "quit"),
        ]

    def move_up(self) -> None:
        """上移光标"""
        self.selected = (self.selected - 1) % len(self.items)

    def move_down(self) -> None:
        """下移光标"""
        self.selected = (self.selected + 1) % len(self.items)

    def get_selected_action(self) -> str:
        """获取选中项的 action"""
        return self.items[self.selected].action

    def execute_action(self, action: str) -> None:
        """执行操作"""
        handler = self._actions.get(action)
        if handler:
            self.message = handler()

    def quit(self) -> None:
        """退出"""
        self.running = False

    def run(self) -> None:
        """启动 TUI"""
        if os.getenv("TERM") is None:
            # 无终端环境，跳过 curses
            return
        curses.wrapper(self._main_loop)

    def _main_loop(self, stdscr: curses.window) -> None:
        """curses 主循环"""
        curses.curs_set(0)  # 隐藏光标
        stdscr.nodelay(False)

        while self.running:
            self._draw(stdscr)
            key = stdscr.getch()
            self._handle_key(key)

    def _draw(self, stdscr: curses.window) -> None:
        """绘制界面"""
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # 标题
        title = f" AutoSOCKS v{__version__} "
        try:
            stdscr.addstr(0, max(0, (width - len(title)) // 2), title[:width], curses.A_REVERSE)
        except curses.error:
            pass

        # 菜单
        start_y = 3
        for i, item in enumerate(self.items):
            y = start_y + i
            if y >= height - 2:
                break
            label = f"  ▸ {item.label}" if i == self.selected else f"    {item.label}"
            try:
                if i == self.selected:
                    stdscr.addstr(y, 4, label[:width - 4], curses.A_REVERSE)
                else:
                    stdscr.addstr(y, 4, label[:width - 4])
            except curses.error:
                pass

        # 消息区
        if self.message:
            msg_y = start_y + len(self.items) + 2
            if msg_y < height - 1:
                lines = self.message.split("\n")
                for j, line in enumerate(lines):
                    if msg_y + j < height - 1:
                        try:
                            stdscr.addstr(msg_y + j, 2, line[:width - 4])
                        except curses.error:
                            pass

        # 底部提示
        try:
            stdscr.addstr(height - 1, 2, " ↑↓ 选择  Enter 执行  q 退出 ", curses.A_DIM)
        except curses.error:
            pass

        stdscr.refresh()

    def _handle_key(self, key: int) -> None:
        """处理按键"""
        if key == curses.KEY_UP or key == ord("k"):
            self.move_up()
        elif key == curses.KEY_DOWN or key == ord("j"):
            self.move_down()
        elif key == ord("\n") or key == curses.KEY_ENTER:
            action = self.get_selected_action()
            self.execute_action(action)
        elif key == ord("q"):
            self.quit()

    # ── 操作实现 ──

    def _do_start(self) -> str:
        if os.geteuid() != 0:
            return "需要 root 权限，请使用 sudo autosocks tui"
        config = load_config(CONFIG_PATH)
        if not config.get("server_host"):
            return "未配置服务器地址，请先选择 [配置服务器]"
        if service_is_active():
            return f"代理已在运行: {config['server_user']}@{config['server_host']}:{config['local_port']}"
        if service_start():
            return f"已启动: {config['server_user']}@{config['server_host']}:{config['local_port']}"
        return "启动失败，请检查日志"

    def _do_stop(self) -> str:
        if os.geteuid() != 0:
            return "需要 root 权限"
        if not service_is_active():
            return "代理未在运行"
        if service_stop():
            return "已停止"
        return "停止失败"

    def _do_restart(self) -> str:
        if os.geteuid() != 0:
            return "需要 root 权限"
        if service_restart():
            return "已重启"
        return "重启失败"

    def _do_status(self) -> str:
        config = load_config(CONFIG_PATH)
        server = f"{config.get('server_user', 'root')}@{config.get('server_host', '未配置')}"
        port = str(config.get('local_port', 1080))
        active = service_is_active()
        status = "运行中" if active else "未运行"
        return f"状态: {status}\n服务器: {server}\n端口: {port}"

    def _do_install(self) -> str:
        # TUI 内的 install 暂不支持交互输入（curses 接管了终端）
        # 提示用户退出后用 CLI
        return "请退出 TUI 后运行: autosocks install"

    def _do_quit(self) -> str:
        self.quit()
        return ""
