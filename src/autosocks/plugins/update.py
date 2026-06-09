"""自更新 - 检查和安装新版本"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from typing import Optional


# PyPI JSON API（零依赖）
_PIP_INDEX_URL = "https://pypi.org/pypi/autosocks/json"


def check_latest_version() -> Optional[str]:
    """检查 PyPI 上的最新版本号。

    Returns:
        最新版本号字符串，网络错误返回 None
    """
    try:
        req = urllib.request.Request(_PIP_INDEX_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data["info"]["version"]
    except Exception:
        return None


def perform_update() -> bool:
    """执行 pip install --upgrade autosocks。

    Returns:
        True 更新成功，False 失败
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "autosocks"],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
