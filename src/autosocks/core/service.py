"""systemd 服务管理"""
from __future__ import annotations

import subprocess


SERVICE_NAME = "autosocks"


def service_start() -> bool:
    """启动 systemd 服务。

    Returns:
        True 成功，False 失败
    """
    result = subprocess.run(
        ["systemctl", "start", SERVICE_NAME],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def service_stop() -> bool:
    """停止 systemd 服务。

    Returns:
        True 成功，False 失败
    """
    result = subprocess.run(
        ["systemctl", "stop", SERVICE_NAME],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def service_restart() -> bool:
    """重启 systemd 服务。

    Returns:
        True 成功，False 失败
    """
    result = subprocess.run(
        ["systemctl", "restart", SERVICE_NAME],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def service_is_active() -> bool:
    """检查 systemd 服务是否正在运行。

    Returns:
        True 正在运行，False 未运行
    """
    result = subprocess.run(
        ["systemctl", "is-active", SERVICE_NAME],
        capture_output=True, text=True,
    )
    return result.returncode == 0
