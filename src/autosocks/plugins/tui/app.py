"""TUI L3 全屏交互界面 - curses 主界面"""
from __future__ import annotations

import curses
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from autosocks import __version__
from autosocks.core.config import load_config, save_config
from autosocks.core.service import service_start, service_stop, service_restart, service_is_active


CONFIG_PATH = Path("/etc/autosocks/config.conf")

# 刷新间隔（秒）
_REFRESH_INTERVAL = 2.0


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
        self.message_time = 0.0
        self._last_refresh = 0.0
        self._actions: dict[str, Callable[[], str]] = {
            "start": self._do_start,
            "stop": self._do_stop,
            "restart": self._do_restart,
            "status": self._do_status,
            "install": self._do_install,
            "health": self._do_health,
            "http_proxy": self._do_http_proxy,
            "env": self._do_env,
            "shell_integration": self._do_shell_integration,
            "update": self._do_update,
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
            MenuItem("健康检查", "health"),
            MenuItem("配置服务器", "install"),
            MenuItem("HTTP 代理", "http_proxy"),
            MenuItem("环境变量", "env"),
            MenuItem("Shell 集成", "shell_integration"),
            MenuItem("检查更新", "update"),
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
            self.message_time = time.time()

    def quit(self) -> None:
        """退出"""
        self.running = False

    def run(self) -> None:
        """启动 TUI"""
        if os.getenv("TERM") is None:
            return
        curses.wrapper(self._main_loop)

    def _main_loop(self, stdscr: curses.window) -> None:
        """curses 主循环（后台刷新状态）"""
        curses.curs_set(0)
        stdscr.nodelay(True)  # 非阻塞输入，支持后台刷新

        while self.running:
            self._draw(stdscr)
            key = stdscr.getch()
            if key != -1:
                self._handle_key(key, stdscr)
            time.sleep(0.05)  # 50ms 轮询

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

        # 实时状态栏
        now = time.time()
        if now - self._last_refresh > _REFRESH_INTERVAL:
            self._last_refresh = now
        active = service_is_active()
        status_text = "● 运行中" if active else "○ 未运行"
        status_attr = curses.color_pair(2) if active else curses.color_pair(1)
        try:
            curses.init_pair(1, curses.COLOR_RED, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
        except curses.error:
            status_attr = curses.A_NORMAL
        try:
            stdscr.addstr(1, 4, status_text, status_attr)
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

    def _handle_key(self, key: int, stdscr: curses.window) -> None:
        """处理按键"""
        if key == curses.KEY_UP or key == ord("k"):
            self.move_up()
        elif key == curses.KEY_DOWN or key == ord("j"):
            self.move_down()
        elif key == ord("\n") or key == curses.KEY_ENTER:
            action = self.get_selected_action()
            if action == "install":
                # install 需要挂起 curses 进行交互输入
                self._do_install_interactive(stdscr)
            else:
                self.execute_action(action)
        elif key == ord("q"):
            self.quit()

    def _suspend_curses(self, stdscr: curses.window) -> None:
        """挂起 curses（用于交互输入）"""
        stdscr.clear()
        stdscr.refresh()
        curses.endwin()

    def _resume_curses(self, stdscr: curses.window) -> None:
        """恢复 curses"""
        stdscr.clear()
        stdscr.refresh()
        curses.curs_set(0)

    def _curses_input(self, stdscr: curses.window, prompt: str, default: str = "") -> str:
        """在 curses 内获取用户输入"""
        self._suspend_curses(stdscr)
        hint = f"（默认: {default}）" if default else ""
        try:
            value = input(f"{prompt}{hint}: ").strip()
        except (EOFError, KeyboardInterrupt):
            value = ""
        self._resume_curses(stdscr)
        return value if value else default

    def _curses_select(self, stdscr: curses.window, prompt: str, options: list[str], default: int = 0) -> int:
        """在 curses 内选择"""
        self._suspend_curses(stdscr)
        print(f"\n{prompt}")
        for i, opt in enumerate(options):
            marker = " →" if i == default else "  "
            print(f"{marker} {i + 1}. {opt}")
        print()
        try:
            choice = input(f"请选择 [1-{len(options)}]（默认 {default + 1}）: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = ""
        self._resume_curses(stdscr)
        if not choice:
            return default
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        return default

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
        bind = str(config.get('local_bind', '127.0.0.1'))
        active = service_is_active()
        status = "运行中" if active else "未运行"
        return f"状态: {status}\n服务器: {server}\n端口: {port}\n绑定: {bind}"

    def _do_health(self) -> str:
        from autosocks.plugins.health import check_health
        active = service_is_active()
        if not active:
            return "服务未运行，无法检查"
        config = load_config(CONFIG_PATH)
        port = int(str(config.get('local_port', 1080)))
        result = check_health(port)
        lines = [
            f"服务状态: {'运行中' if result.service_active else '未运行'}",
            f"代理可用: {'是' if result.proxy_ok else '否'}",
        ]
        if result.exit_ip:
            lines.append(f"出口 IP: {result.exit_ip}")
        lines.append(f"健康状态: {result.status.value}")
        return "\n".join(lines)

    def _do_install_interactive(self, stdscr: curses.window) -> None:
        """在 TUI 内完成交互式配置"""
        if os.geteuid() != 0:
            self.message = "需要 root 权限"
            self.message_time = time.time()
            return

        server_input = self._curses_input(stdscr, "服务器地址（user@host[:port]）")
        if not server_input:
            self.message = "已取消"
            self.message_time = time.time()
            return

        # 解析
        if "@" in server_input:
            user, host_part = server_input.split("@", 1)
        else:
            user = "root"
            host_part = server_input

        if ":" in host_part:
            host, port_str = host_part.rsplit(":", 1)
            server_port = int(port_str) if port_str.isdigit() else 22
        else:
            host = host_part
            server_port = 22

        local_port_str = self._curses_input(stdscr, "本地 SOCKS5 端口", "1080")
        local_port = int(local_port_str) if local_port_str.isdigit() else 1080

        auth_idx = self._curses_select(stdscr, "认证方式", ["SSH 密钥", "密码认证"], 0)
        auth_type = "key" if auth_idx == 0 else "password"
        key_path = self._curses_input(stdscr, "SSH 密钥路径", "~/.ssh/id_rsa") if auth_type == "key" else ""

        confirm = self._curses_select(stdscr, "确认保存？", ["是，保存", "否，取消"], 0)
        if confirm != 0:
            self.message = "已取消"
            self.message_time = time.time()
            return

        config = {
            "server_host": host,
            "server_user": user,
            "server_port": server_port,
            "local_port": local_port,
            "auth_type": auth_type,
            "auth_key_path": key_path,
        }
        save_config(CONFIG_PATH, config)
        self.message = f"配置已保存: {user}@{host}:{server_port}"
        self.message_time = time.time()

    def _do_install(self) -> str:
        # 由 _do_install_interactive 处理，这里不应被直接调用
        return ""

    def _do_http_proxy(self) -> str:
        from autosocks.plugins.proxy import start_http_proxy, detect_gost
        if not service_is_active():
            return "代理服务未运行，请先启动"

        gost = detect_gost()
        if not gost:
            return "未检测到 gost，请先安装 gost\n  https://github.com/ginuerzh/gost"

        config = load_config(CONFIG_PATH)
        socks_port = int(str(config.get('local_port', 1080)))
        http_port = socks_port + 1

        if start_http_proxy(socks_port, http_port):
            return f"HTTP 代理已启动: 127.0.0.1:{http_port}\nSOCKS5 → HTTP 转发中"
        return "启动失败"

    def _do_env(self) -> str:
        config = load_config(CONFIG_PATH)
        bind = str(config.get('local_bind', '127.0.0.1'))
        port = int(str(config.get('local_port', 1080)))
        proxy = f"socks5://{bind}:{port}"
        return (
            f"环境变量命令（在 shell 中执行）：\n"
            f"  eval \"$(autosocks env)\"\n\n"
            f"当前代理地址：{proxy}\n"
            f"  http_proxy={proxy}\n"
            f"  https_proxy={proxy}\n"
            f"  ALL_PROXY={proxy}"
        )

    def _do_shell_integration(self) -> str:
        from autosocks.plugins.shell_integration import install_integration, uninstall_integration
        script_path = Path.home() / ".autosocks.sh"
        config = load_config(CONFIG_PATH)
        port = int(str(config.get('local_port', 1080)))

        idx = self._curses_select_static("Shell 集成", ["安装到 ~/.autosocks.sh", "卸载"], 0)
        if idx == 0:
            install_integration(script_path, port)
            return f"已安装 Shell 集成\n添加到 ~/.bashrc:\n  source {script_path}"
        else:
            uninstall_integration(script_path)
            return "已卸载 Shell 集成"

    def _curses_select_static(self, prompt: str, options: list[str], default: int = 0) -> int:
        """非 curses 环境的静态选择（shell 中）"""
        print(f"\n{prompt}")
        for i, opt in enumerate(options):
            marker = " →" if i == default else "  "
            print(f"{marker} {i + 1}. {opt}")
        print()
        try:
            choice = input(f"请选择 [1-{len(options)}]（默认 {default + 1}）: ").strip()
        except (EOFError, KeyboardInterrupt):
            return default
        if not choice:
            return default
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        return default

    def _do_update(self) -> str:
        from autosocks.plugins.update import check_latest_version, perform_update
        from autosocks import __version__ as current

        latest = check_latest_version()
        if latest is None:
            return "无法检查更新（网络错误）"

        if latest == current:
            return f"已是最新版本: v{current}"

        msg = f"发现新版本: v{latest}（当前 v{current}）\n"
        if perform_update():
            return msg + "更新成功！请重启 autosocks"
        return msg + "更新失败，请手动运行:\n  sudo pip install --upgrade autosocks"

    def _do_quit(self) -> str:
        self.quit()
        return ""
