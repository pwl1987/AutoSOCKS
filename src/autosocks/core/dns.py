"""远程 DNS 解析 (DoH)

解决 SSH 动态转发 (-D) 模式下 DNS 污染问题：
  - curl / 浏览器等客户端默认本地解析，会把 api.openai.com → Facebook IP
  - SSH -D 走的是客户端已解析的 IP，无法拦截
  - 本模块使用 DoH (DNS over HTTPS) 走代理获取真实 IP，再交给 curl --resolve

设计要点：
  - 走 SOCKS5 代理（127.0.0.1:1080）调用 DoH，绕过本地污染 DNS
  - 多上游轮询：1.1.1.1 (Cloudflare) / 8.8.8.8 (Google) / 9.9.9.9 (Quad9)
  - 失败时回退到本地 getent
  - 简单进程内 TTL 缓存，避免重复解析
"""
from __future__ import annotations

import json
import socket
import subprocess
import time
from typing import Optional

# DoH 上游列表（轮询，第一个可用即返回）
_DOH_UPSTREAMS = (
    "https://1.1.1.1/dns-query",
    "https://8.8.8.8/dns-query",
    "https://9.9.9.9/dns-query",
)

# 简单 TTL 缓存
_CACHE: dict[str, tuple[float, str]] = {}
_CACHE_TTL = 300.0  # 5 分钟


def resolve_remote(
    domain: str,
    proxy_port: Optional[int] = None,
    timeout: float = 5.0,
) -> Optional[str]:
    """通过 DoH 远程解析域名，返回 A 记录 IP。

    Args:
        domain: 待解析域名，如 api.openai.com
        proxy_port: SOCKS5 代理端口（走代理解析）；None 时直连 DoH
        timeout: 单次查询超时

    Returns:
        IPv4 地址字符串；解析失败返回 None
    """
    # 已是 IP 直接返回
    if _is_ip(domain):
        return domain

    now = time.time()
    cached = _CACHE.get(domain)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    for upstream in _DOH_UPSTREAMS:
        ip = _query_doh(domain, upstream, proxy_port, timeout)
        if ip:
            _CACHE[domain] = (now, ip)
            return ip

    # DoH 全失败 → 回退本地 getent（污染环境下可能拿到错 IP，但聊胜于无）
    return _fallback_getent(domain)


def _query_doh(
    domain: str,
    upstream: str,
    proxy_port: Optional[int],
    timeout: float,
) -> Optional[str]:
    """查询单个 DoH 上游"""
    try:
        cmd = [
            "curl", "-sS", "--max-time", str(int(timeout)),
            "-H", "Accept: application/dns-json",
            f"{upstream}?name={domain}&type=A",
        ]
        if proxy_port:
            cmd[2:2] = ["--socks5-hostname", f"127.0.0.1:{proxy_port}"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 2,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        for ans in data.get("Answer", []):
            if ans.get("type") == 1:  # A 记录
                ip = str(ans.get("data", ""))
                if _is_ip(ip):
                    return ip
        return None
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
        return None


def _fallback_getent(domain: str) -> Optional[str]:
    """本地 getent 回退"""
    try:
        infos = socket.getaddrinfo(domain, None, type=socket.SOCK_STREAM)
        for info in infos:
            sockaddr = info[4]
            if sockaddr and sockaddr[0]:
                ip = str(sockaddr[0])
                if _is_ip(ip) and ":" not in ip:  # 只取 IPv4
                    return ip
        return None
    except (socket.gaierror, OSError):
        return None


def _is_ip(addr: str) -> bool:
    """判断是否为 IP 地址字面量"""
    try:
        socket.inet_aton(addr)
        return True
    except OSError:
        return False


def clear_cache() -> None:
    """清空解析缓存（测试用）"""
    _CACHE.clear()