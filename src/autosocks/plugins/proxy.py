"""HTTP 代理管理 - gost/privoxy SOCKS5→HTTP 转发"""
from __future__ import annotations

import shutil
import subprocess
from typing import Optional


# gost 进程句柄（全局，用于停止）
_gost_process: Optional[subprocess.Popen[bytes]] = None


def detect_gost() -> Optional[str]:
    """检测系统是否安装了 gost。

    Returns:
        gost 可执行文件路径，未安装返回 None
    """
    return shutil.which("gost")


def generate_gost_command(socks_port: int, http_port: int, bind: str = "127.0.0.1") -> list[str]:
    """生成 gost SOCKS5→HTTP 转发命令。

    Args:
        socks_port: 上游 SOCKS5 端口
        http_port: 本地 HTTP 代理端口
        bind: 绑定地址

    Returns:
        命令参数列表
    """
    gost_path = detect_gost() or "gost"
    return [
        gost_path,
        "-L", f"http://{bind}:{http_port}",
        "-F", f"socks5://127.0.0.1:{socks_port}",
    ]


def generate_privoxy_config(socks_port: int, http_port: int, bind: str = "127.0.0.1") -> str:
    """生成 Privoxy 配置文件内容。

    Args:
        socks_port: 上游 SOCKS5 端口
        http_port: 本地 HTTP 代理端口
        bind: 监听地址

    Returns:
        Privoxy 配置文件内容
    """
    return f"""listen-address {bind}:{http_port}
forward-socks5t / 127.0.0.1:{socks_port} .
"""


def start_http_proxy(socks_port: int, http_port: int, bind: str = "127.0.0.1") -> bool:
    """启动 HTTP 代理（优先使用 gost）。

    Args:
        socks_port: 上游 SOCKS5 端口
        http_port: 本地 HTTP 代理端口
        bind: 绑定地址

    Returns:
        True 启动成功，False 失败
    """
    global _gost_process

    gost_path = detect_gost()
    if not gost_path:
        return False

    cmd = generate_gost_command(socks_port, http_port, bind)
    try:
        _gost_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, FileNotFoundError):
        return False


def stop_http_proxy() -> bool:
    """停止 HTTP 代理进程。

    Returns:
        True 成功，False 失败
    """
    global _gost_process

    if _gost_process is None:
        return True

    proc = _gost_process

    try:
        proc.terminate()
        proc.wait(timeout=5)
        _gost_process = None
        return True
    except Exception:
        try:
            proc.kill()
            _gost_process = None
            return True
        except Exception:
            return False
