"""SSH 隧道管理"""
from __future__ import annotations

import shutil
import subprocess
from typing import Optional


def build_ssh_command(config: dict[str, object]) -> list[str]:
    """构建 SSH SOCKS5 隧道命令行。

    支持密钥认证 (auth_type=key) 和密码认证 (auth_type=password)。
    密码认证使用 sshpass（需系统安装 sshpass）。

    Args:
        config: 配置字典

    Returns:
        SSH 命令参数列表
    """
    host = config["server_host"]
    user = config["server_user"]
    port = str(config["server_port"])
    local_port = str(config["local_port"])
    bind = config["local_bind"]
    keepalive = str(config["ssh_keepalive"])
    timeout = str(config["ssh_timeout"])
    auth_type = config["auth_type"]
    key_path = config.get("auth_key_path", "")
    auth_password = config.get("auth_password", "")

    cmd = [
        "ssh",
        "-D", f"{bind}:{local_port}",
        "-N",
        "-p", port,
        "-o", f"ServerAliveInterval={keepalive}",
        "-o", f"ConnectTimeout={timeout}",
        "-o", "StrictHostKeyChecking=accept-new",
    ]

    if auth_type == "key" and key_path:
        cmd.extend(["-i", str(key_path)])
    elif auth_type == "password" and auth_password:
        # 使用 sshpass 传递密码
        sshpass_path = shutil.which("sshpass")
        if sshpass_path:
            cmd = [sshpass_path, "-p", str(auth_password)] + cmd
            # 密码认证时禁用公钥认证，避免尝试密钥
            cmd.extend(["-o", "PreferredAuthentications=password"])

    cmd.append(f"{user}@{host}")

    return cmd


def check_proxy(port: int) -> bool:
    """检查 SOCKS5 代理是否可用。

    Args:
        port: 本地 SOCKS5 端口

    Returns:
        True 可用，False 不可用
    """
    try:
        result = subprocess.run(
            [
                "curl", "-s",
                "--socks5", f"127.0.0.1:{port}",
                "--max-time", "5",
                "https://cp.cloudflare.com",
            ],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_exit_ip(port: int) -> Optional[str]:
    """通过 SOCKS5 代理获取出口 IP。

    Args:
        port: 本地 SOCKS5 端口

    Returns:
        出口 IP 字符串，失败返回 None
    """
    try:
        result = subprocess.run(
            [
                "curl", "-s",
                "--socks5", f"127.0.0.1:{port}",
                "--max-time", "10",
                "https://ifconfig.me",
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
