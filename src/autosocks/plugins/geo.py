"""GeoIP 分流 - 国内 IP 列表加载和匹配"""
from __future__ import annotations

import ipaddress
import urllib.request
from pathlib import Path


# 默认国内 IP 列表 URL
DEFAULT_IP_LIST_URL = "https://raw.githubusercontent.com/apricot-suit/chinanet-list/main/china_ip_list.txt"


def load_ip_list(path: Path) -> list[ipaddress.IPv4Network]:
    """从文件加载 CIDR 格式的 IP 列表。

    Args:
        path: IP 列表文件路径

    Returns:
        IPv4Network 列表
    """
    networks: list[ipaddress.IPv4Network] = []

    if not path.exists():
        return networks

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            networks.append(ipaddress.IPv4Network(line, strict=False))
        except ValueError:
            continue

    return networks


def is_china_ip(ip_str: str, networks: list[ipaddress.IPv4Network]) -> bool:
    """判断 IP 是否在给定网络列表中。

    Args:
        ip_str: IP 地址字符串
        networks: IPv4Network 列表

    Returns:
        True 在列表中，False 不在
    """
    try:
        addr = ipaddress.IPv4Address(ip_str)
    except ValueError:
        return False

    for net in networks:
        if addr in net:
            return True

    return False


def update_ip_list(path: Path, url: str = DEFAULT_IP_LIST_URL) -> bool:
    """从远程下载最新的国内 IP 列表。

    Args:
        path: 保存路径
        url: 下载 URL

    Returns:
        True 成功，False 失败
    """
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return True
    except Exception:
        return False
