"""TUI L3 实时仪表盘 - 状态面板渲染"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DashboardData:
    """仪表盘数据"""
    status: str          # healthy / degraded / down
    server: str          # user@host
    port: int            # SOCKS5 端口
    exit_ip: str | None  # 出口 IP
    latency_ms: float    # 延迟（毫秒，-1 表示不可用）
    uptime: str          # 运行时间


def render_dashboard(data: DashboardData) -> str:
    """渲染仪表盘为字符串（用于 curses 或终端输出）。

    Args:
        data: 仪表盘数据

    Returns:
        格式化的仪表盘字符串
    """
    # 状态图标
    status_icons = {
        "healthy": "🟢",
        "degraded": "🟡",
        "down": "🔴",
    }
    icon = status_icons.get(data.status, "⚪")

    # 延迟显示
    if data.latency_ms >= 0:
        latency_str = f"{data.latency_ms:.1f}ms"
    else:
        latency_str = "N/A"

    # 出口 IP
    exit_ip = data.exit_ip or "N/A"

    lines = [
        "┏━━━ AutoSOCKS Dashboard ━━━┓",
        "┃                            ┃",
        f"┃ {icon} Status:   {data.status:<10} ┃",
        f"┃ 📍 Server:   {data.server:<10} ┃",
        f"┃ 🔌 SOCKS5:   {data.port:<10} ┃",
        f"┃ 🌍 Exit IP:  {exit_ip:<10} ┃",
        f"┃ ⏱️  Latency:  {latency_str:<10} ┃",
        f"┃ ⏰ Uptime:   {data.uptime:<10} ┃",
        "┃                            ┃",
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
    ]

    return "\n".join(lines)
