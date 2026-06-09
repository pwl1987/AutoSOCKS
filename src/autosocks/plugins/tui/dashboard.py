"""TUI L3 实时仪表盘 - 状态面板渲染

支持：
- 状态图标（healthy / degraded / down）
- 延迟颜色分级
- 出口 IP 显示
- 运行时间计算
- curses 和纯终端两种输出模式
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DashboardData:
    """仪表盘数据"""
    status: str              # healthy / degraded / down
    server: str              # user@host
    port: int                # SOCKS5 端口
    bind: str = "127.0.0.1"  # 绑定地址
    exit_ip: str | None = None   # 出口 IP
    latency_ms: float = -1.0     # 延迟（毫秒，-1 表示不可用）
    uptime: str = ""             # 运行时间
    auth_type: str = "key"       # 认证方式
    reconnect: bool = True       # 自动重连
    log_enabled: bool = True     # 日志开启
    profile_name: str = ""       # 当前 profile 名称


# 延迟等级
def _latency_display(ms: float) -> tuple[str, str]:
    """返回 (显示文本, ANSI颜色代码)"""
    if ms < 0:
        return "N/A", "\033[0;90m"
    elif ms < 100:
        return f"{ms:.0f}ms", "\033[0;32m"  # 绿色
    elif ms < 300:
        return f"{ms:.0f}ms", "\033[0;33m"  # 黄色
    else:
        return f"{ms:.0f}ms", "\033[0;31m"  # 红色


# 状态图标
_STATUS_ICONS = {
    "healthy": "\033[0;32m●\033[0m",    # 绿色圆点
    "degraded": "\033[0;33m●\033[0m",   # 黄色圆点
    "down": "\033[0;31m●\033[0m",       # 红色圆点
}

_STATUS_ICONS_PLAIN = {
    "healthy": "●",
    "degraded": "●",
    "down": "○",
}


def render_dashboard(data: DashboardData) -> str:
    """渲染仪表盘为字符串（用于纯终端输出）。

    Args:
        data: 仪表盘数据

    Returns:
        格式化的仪表盘字符串
    """
    _G = "\033[1;32m"  # 绿色边框
    _C = "\033[0m"     # 重置
    _B = "\033[1m"     # 粗体
    _D = "\033[0;90m"  # 暗色
    _W = "\033[0;37m"  # 白色

    icon = _STATUS_ICONS_PLAIN.get(data.status, "○")
    lat_text, _ = _latency_display(data.latency_ms)
    exit_ip = data.exit_ip or "N/A"
    auth = "SSH密钥" if data.auth_type == "key" else "密码"
    recon = "开" if data.reconnect else "关"
    log = "开" if data.log_enabled else "关"

    proxy = f"socks5://{data.bind}:{data.port}"
    http_proxy = f"http://{data.bind}:{data.port + 1}"

    inner = 48
    sep = "━" * (inner + 2)

    lines = [
        f"{_G}┏{sep}┓{_C}",
        f"{_G}┃{_C} {_B}◈ AutoSOCKS Dashboard{_C}{' ' * (inner - 22)} {_G}┃{_C}",
        f"{_G}┣{sep}┫{_C}",
        f"{_G}┃{_C} {icon} 状态:    {_B}{data.status:<12}{_C}{_G}┃{_C}",
        f"{_G}┃{_C} ▸ 服务器:  {_B}{data.server:<22}{_C} {_G}┃{_C}",
        f"{_G}┃{_C} ▸ SOCKS5:  {_B}{f'{data.bind}:{data.port}':<22}{_C} {_G}┃{_C}",
        f"{_G}┃{_C} ▸ HTTP:    {_B}{http_proxy:<22}{_C} {_G}┃{_C}",
        f"{_G}┃{_C} ◎ 出口 IP: {_B}{exit_ip:<22}{_C} {_G}┃{_C}",
        f"{_G}┃{_C} ⏱  延迟:   {_B}{lat_text:<22}{_C} {_G}┃{_C}",
        f"{_G}┃{_C} ⏰ 运行:   {_B}{data.uptime or 'N/A':<22}{_C} {_G}┃{_C}",
        f"{_G}┣{sep}┫{_C}",
        f"{_G}┃{_C} 认证: {auth}  重连: {recon}  日志: {log}{' ' * (inner - 26)} {_G}┃{_C}",
        f"{_G}┃{_C} 代理: {_B}{proxy:<27}{_C} {_G}┃{_C}",
        f"{_G}┃{_C}{' ' * (inner + 2)} {_G}┃{_C}",
        f"{_G}┗{sep}┛{_C}",
    ]

    return "\n".join(lines)


def render_dashboard_plain(data: DashboardData) -> str:
    """渲染无颜色的纯文本仪表盘（用于日志或管道）。

    Args:
        data: 仪表盘数据

    Returns:
        纯文本仪表盘字符串
    """
    lat_text = f"{data.latency_ms:.0f}ms" if data.latency_ms >= 0 else "N/A"
    exit_ip = data.exit_ip or "N/A"
    proxy = f"socks5://{data.bind}:{data.port}"

    lines = [
        "=== AutoSOCKS Dashboard ===",
        f"  Status:  {data.status}",
        f"  Server:  {data.server}",
        f"  SOCKS5:  {data.bind}:{data.port}",
        f"  Exit IP: {exit_ip}",
        f"  Latency: {lat_text}",
        f"  Uptime:  {data.uptime or 'N/A'}",
        f"  Proxy:   {proxy}",
        "===========================",
    ]

    return "\n".join(lines)
