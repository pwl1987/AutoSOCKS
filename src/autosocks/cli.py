"""命令行入口 - 参数解析和命令分发"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from autosocks import __version__
from autosocks.core.config import load_config, save_config
from autosocks.core.errors import show_error
from autosocks.core.output import print_error, print_warning
from autosocks.core.service import service_start, service_stop, service_restart, service_is_active
from autosocks.core.tunnel import build_ssh_command
from autosocks.plugins.env import env_set, env_unset
from autosocks.plugins.tui.beautify import panel, divider
from autosocks.plugins.tui.menu import select_option, input_text


CONFIG_PATH = Path("/etc/autosocks/config.conf")


def check_root() -> bool:
    """检查是否有 root 权限。"""
    if os.geteuid() != 0:
        show_error("E001")
        return False
    return True


def main(args: list[str] | None = None) -> None:
    """主入口函数。"""
    if args is None:
        args = sys.argv[1:]

    command = args[0] if args else "help"

    match command:
        case "help":
            _show_help()
        case "version":
            _show_version()
        case "start":
            _cmd_start()
        case "stop":
            _cmd_stop()
        case "restart":
            _cmd_restart()
        case "status":
            _cmd_status()
        case "env":
            _cmd_env(args[1:])
        case "install":
            _cmd_install()
        case "--daemon":
            _cmd_daemon()
        case _:
            print_error(f"未知命令：{command}", "E012")
            sys.exit(2)


def _show_help() -> None:
    """显示帮助信息。"""
    panel("AutoSOCKS - 极简Linux代理工具", [
        "",
        "常用命令：",
        "  autosocks install   交互式配置",
        "  autosocks start     启动代理",
        "  autosocks stop      停止代理",
        "  autosocks restart   重启代理",
        "  autosocks status    查看状态",
        "  autosocks env       设置代理环境变量",
        "  autosocks version   显示版本",
    ])


def _show_version() -> None:
    """显示版本号。"""
    panel("AutoSOCKS", [f"版本  v{__version__}"])


def _cmd_start() -> None:
    """启动代理服务。"""
    if not check_root():
        return

    config = load_config(CONFIG_PATH)
    if not config.get("server_host"):
        panel("启动失败", [
            "未配置服务器地址",
            "",
            "运行 autosocks install 进行配置",
        ])
        return

    if service_is_active():
        panel("代理服务已在运行", [
            f"服务器  {config['server_user']}@{config['server_host']}",
            f"端口    {config['local_port']}",
        ])
        return

    if not service_start():
        panel("启动失败", ["服务启动失败，请检查日志"])
        return

    panel("AutoSOCKS 已启动", [
        f"服务器  {config['server_user']}@{config['server_host']}",
        f"端口    {config['local_port']}",
    ])


def _cmd_stop() -> None:
    """停止代理服务。"""
    if not check_root():
        return

    if not service_is_active():
        panel("提示", ["代理服务未在运行"])
        return

    if not service_stop():
        panel("停止失败", ["服务停止失败，请检查日志"])
        return

    panel("AutoSOCKS 已停止", [])


def _cmd_restart() -> None:
    """重启代理服务。"""
    if not check_root():
        return

    config = load_config(CONFIG_PATH)

    if not service_restart():
        panel("重启失败", ["服务重启失败，请检查日志"])
        return

    panel("AutoSOCKS 已重启", [
        f"服务器  {config.get('server_user', 'root')}@{config.get('server_host', '')}",
        f"端口    {config.get('local_port', 1080)}",
    ])


def _cmd_status() -> None:
    """查看代理状态。"""
    if not check_root():
        return

    config = load_config(CONFIG_PATH)
    server = f"{config.get('server_user', 'root')}@{config.get('server_host', '未配置')}"
    port = str(config.get('local_port', 1080))
    bind = str(config.get('local_bind', '127.0.0.1'))

    if service_is_active():
        panel("代理状态 - 运行中", [
            f"服务器    {server}",
            f"本地端口  {port}",
            f"绑定地址  {bind}",
        ])
    else:
        panel("代理状态 - 未运行", [
            f"服务器    {server}",
            f"本地端口  {port}",
            "",
            "运行 autosocks start 启动代理",
        ])


def _cmd_env(sub_args: list[str]) -> None:
    """输出环境变量设置/清除命令。"""
    if sub_args and sub_args[0] == "unset":
        env_unset()
        return

    config = load_config(CONFIG_PATH)
    bind = str(config.get("local_bind", "127.0.0.1"))
    port = int(str(config.get("local_port", 1080)))
    env_set(bind, port)


def _cmd_install() -> None:
    """交互式配置向导（TUI）。"""
    if not check_root():
        return

    panel("AutoSOCKS 配置向导", ["让我们配置你的代理服务器"])

    # 服务器地址
    server_input = input_text("服务器地址（user@host[:port]）", required=True)
    if not server_input:
        return

    # 解析 user@host[:port]
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

    # 本地端口
    local_port_str = input_text("本地 SOCKS5 端口", default="1080")
    local_port = int(local_port_str) if local_port_str.isdigit() else 1080

    # 认证方式
    auth_idx = select_option(
        "认证方式",
        ["SSH 密钥", "密码认证"],
        default=0,
    )
    auth_type = "key" if auth_idx == 0 else "password"

    if auth_type == "key":
        key_path = input_text("SSH 密钥路径", default="~/.ssh/id_rsa")
    else:
        key_path = ""

    # 确认
    divider()
    panel("配置预览", [
        f"服务器    {user}@{host}:{server_port}",
        f"本地端口  {local_port}",
        f"认证方式  {auth_type}" + (f" ({key_path})" if key_path else ""),
    ])

    confirm = select_option("确认保存？", ["是，保存配置", "否，取消"], default=0)
    if confirm != 0:
        print_warning("已取消")
        return

    # 保存配置
    config = {
        "server_host": host,
        "server_user": user,
        "server_port": server_port,
        "local_port": local_port,
        "auth_type": auth_type,
        "auth_key_path": key_path,
    }

    save_config(CONFIG_PATH, config)
    divider()
    panel("配置完成", [
        "配置已保存到 " + str(CONFIG_PATH),
        "",
        "下一步：",
        "  autosocks start    启动代理",
        "  autosocks status   查看状态",
        "  autosocks env      设置环境变量",
    ])


def _cmd_daemon() -> None:
    """守护进程模式（systemd ExecStart 使用）。"""
    config = load_config(CONFIG_PATH)

    if not config.get("server_host"):
        print_error("未配置服务器地址")
        sys.exit(1)

    cmd = build_ssh_command(config)

    process = None
    try:
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        if process:
            process.terminate()
            process.wait()
    except FileNotFoundError:
        print_error("SSH 未安装", "E007")
        sys.exit(1)
