"""自更新 - 检查和安装新版本"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from typing import Optional


# GitHub API（检查最新 tag）
_GITHUB_API_URL = "https://api.github.com/repos/pwl1987/AutoSOCKS/tags"

# 安装源（从 GitHub main 分支安装）
_INSTALL_SOURCE = "autosocks @ git+https://github.com/pwl1987/AutoSOCKS.git@main"


def check_latest_version() -> Optional[str]:
    """检查 GitHub 上的最新版本号。

    Returns:
        最新版本号字符串，网络错误返回 None
    """
    try:
        req = urllib.request.Request(_GITHUB_API_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data and isinstance(data, list):
                return data[0]["name"].lstrip("v")
            return None
    except Exception:
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
