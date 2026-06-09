"""Webhook 告警 - 发送通知到外部服务"""
from __future__ import annotations

import json
import urllib.request


def send_webhook(url: str, message: str) -> bool:
    """发送 Webhook 告警。

    Args:
        url: Webhook URL
        message: 告警消息

    Returns:
        True 成功，False 失败
    """
    try:
        payload = json.dumps({"text": message, "source": "autosocks"}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception:
        return False
