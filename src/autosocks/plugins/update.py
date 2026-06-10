"""自更新 - 检查和安装新版本"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from typing import Optional

from autosocks.core.dns import resolve_remote


# GitHub API（检查最新 tag）
_GITHUB_API_HOST = "api.github.com"
_GITHUB_API_URL = f"https://{_GITHUB_API_HOST}/repos/pwl1987/AutoSOCKS/tags"

# 安装源（从 GitHub main 分支安装）
_INSTALL_SOURCE = "autosocks @ git+https://github.com/pwl1987/AutoSOCKS.git@main"


def check_latest_version() -> Optional[str]:
    """检查 GitHub 上的最新版本号。

    自动检测本地 SOCKS5 代理（ALL_PROXY / autosocks 服务），
    走 DoH 远端解析绕过 DNS 污染。

    Returns:
        最新版本号字符串，网络错误返回 None
    """
    try:
        req = urllib.request.Request(_GITHUB_API_URL, headers={"Accept": "application/json"})

        # 尝试通过 DoH 预解析 api.github.com（绕过 DNS 污染）
        ip = resolve_remote(_GITHUB_API_HOST)
        if ip:
            # 用 --resolve 的 curl 获取（比 urllib 更可靠地走代理）
            return _check_via_curl(ip)

        # 回退：urllib 直连（依赖系统代理/直连）
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data and isinstance(data, list):
                first_tag = data[0]
                if isinstance(first_tag, dict):
                    name: str = str(first_tag.get("name", ""))
                    return name.lstrip("v") if name else None
            return None
    except Exception:
        return None


def _check_via_curl(resolved_ip: str) -> Optional[str]:
    """通过 curl + --resolve 检查版本（走 SOCKS5 代理 + DoH 解析）"""
    proxy_port = _detect_proxy_port()
    cmd = [
        "curl", "-sS", "--max-time", "10",
        "--resolve", f"{_GITHUB_API_HOST}:443:{resolved_ip}",
    ]
    if proxy_port:
        cmd[2:2] = ["--socks5-hostname", f"127.0.0.1:{proxy_port}"]
    cmd.append(_GITHUB_API_URL)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return None
    data = json.loads(result.stdout)
    if data and isinstance(data, list):
        first_tag = data[0]
        if isinstance(first_tag, dict):
            name: str = str(first_tag.get("name", ""))
            return name.lstrip("v") if name else None
    return None


def _detect_proxy_port() -> Optional[int]:
    """检测本地 SOCKS5 代理端口"""
    # 1. 环境变量
    all_proxy = os.environ.get("ALL_PROXY") or os.environ.get("all_proxy") or ""
    if "socks5" in all_proxy.lower():
        try:
            return int(all_proxy.rsplit(":", 1)[-1].rstrip("/"))
        except (ValueError, IndexError):
            pass
    # 2. autosocks 默认 1080
    try:
        result = subprocess.run(
            ["ss", "-lntp"], capture_output=True, text=True, timeout=3,
        )
        if ":1080" in result.stdout:
            return 1080
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def perform_update() -> bool:
    """执行从 GitHub 安装最新版本。

    Returns:
        True 更新成功，False 失败
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", _INSTALL_SOURCE],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
