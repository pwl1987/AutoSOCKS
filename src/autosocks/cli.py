"""命令行入口 - 参数解析和命令分发"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from autosocks import __version__
from autosocks.core.config import load_config
from autosocks.core.errors import show_error
from autosocks.core.output import print_success, print_error, print_warning, print_info
from autosocks.core.service import service_start, service_stop, service_restart, service_is_active
from autosocks.plugins.env import env_set, env_unset


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
        case _:
            print_error(f"未知命令：{command}", "E012")
            sys.exit(2)


def _show_help() -> None:
    """显示帮助信息。"""
    print()
    print("AutoSOCKS - 极简Linux代理工具")
    print()
    print("常用命令：")
    print("  autosocks status     查看状态")
    print("  autosocks start      启动代理")
    print("  autosocks stop       停止代理")
    print("  autosocks restart    重启代理")
    print("  autosocks env        设置代理环境变量")
    print("  autosocks version    显示版本")
    print()


def _show_version() -> None:
    """显示版本号。"""
    print(f"AutoSOCKS v{__version__}")


def _cmd_start() -> None:
    """启动代理服务。"""
    if not check_root():
        return

    config = load_config(CONFIG_PATH)
    if not config.get("server_host"):
        print_error("未配置服务器地址", "E006")
        print_info("运行 autosocks install 进行安装配置")
        return

    if service_is_active():
        print_warning("代理服务已在运行中")
        print(f"  服务器：{config['server_user']}@{config['server_host']}")
        print(f"  本地端口：{config['local_port']}")
        return

    print("正在启动代理服务...")
    if not service_start():
        print_error("服务启动失败")
        return

    print_success("AutoSOCKS 已启动")
    print(f"  服务器：{config['server_user']}@{config['server_host']}")
    print(f"  本地端口：{config['local_port']}")


def _cmd_stop() -> None:
    """停止代理服务。"""
    if not check_root():
        return

    if not service_is_active():
        print_warning("代理服务未在运行")
        return

    print("正在停止代理服务...")
    if not service_stop():
        print_error("服务停止失败")
        return

    print_success("AutoSOCKS 已停止")


def _cmd_restart() -> None:
    """重启代理服务。"""
    if not check_root():
        return

    config = load_config(CONFIG_PATH)

    print("正在重启代理服务...")
    if not service_restart():
        print_error("服务重启失败")
        return

    print_success("AutoSOCKS 已重启")
    print(f"  服务器：{config.get('server_user', 'root')}@{config.get('server_host', '')}")
    print(f"  本地端口：{config.get('local_port', 1080)}")


def _cmd_status() -> None:
    """查看代理状态。"""
    if not check_root():
        return

    config = load_config(CONFIG_PATH)

    if service_is_active():
        print_success("代理服务运行中")
        print(f"  服务器：{config.get('server_user', 'root')}@{config.get('server_host', '未配置')}")
        print(f"  本地端口：{config.get('local_port', 1080)}")
        print(f"  绑定地址：{config.get('local_bind', '127.0.0.1')}")
    else:
        print_warning("代理服务未运行")
        print_info("运行 autosocks start 启动代理")


def _cmd_env(sub_args: list[str]) -> None:
    """输出环境变量设置/清除命令。"""
    if sub_args and sub_args[0] == "unset":
        env_unset()
        return

    config = load_config(CONFIG_PATH)
    bind = str(config.get("local_bind", "127.0.0.1"))
    port = int(str(config.get("local_port", 1080)))
    env_set(bind, port)
