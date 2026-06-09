"""健康检查 - 服务状态、代理可用性、延迟检测"""
from __future__ import annotations

import enum
import subprocess
import time
from dataclasses import dataclass

from autosocks.core.service import service_is_active
from autosocks.core.tunnel import check_proxy, get_exit_ip


class HealthStatus(enum.Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class HealthResult:
    """健康检查结果"""
    status: HealthStatus
    service_active: bool
    proxy_ok: bool
    exit_ip: str | None = None
    message: str = ""


def check_health(port: int = 1080) -> HealthResult:
    """执行健康检查。

    Args:
        port: SOCKS5 端口

    Returns:
        HealthResult 健康检查结果
    """
    active = service_is_active()

    if not active:
        return HealthResult(
            status=HealthStatus.DOWN,
            service_active=False,
            proxy_ok=False,
            message="服务未运行",
        )

    proxy_ok = check_proxy(port)
    exit_ip = get_exit_ip(port) if proxy_ok else None

    if proxy_ok:
        return HealthResult(
            status=HealthStatus.HEALTHY,
            service_active=True,
            proxy_ok=True,
            exit_ip=exit_ip,
            message="服务正常",
        )
    else:
        return HealthResult(
            status=HealthStatus.DEGRADED,
            service_active=True,
            proxy_ok=False,
            message="服务运行但代理不可用",
        )


def check_latency(port: int = 1080, samples: int = 3) -> list[float]:
    """检测代理延迟（多次采样）。

    Args:
        port: SOCKS5 端口
        samples: 采样次数

    Returns:
        每次采样的延迟时间（秒），失败为 -1.0
    """
    results: list[float] = []

    for _ in range(samples):
        start = time.monotonic()
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
            elapsed = time.monotonic() - start
            if result.returncode == 0:
                results.append(elapsed)
            else:
                results.append(-1.0)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            results.append(-1.0)

    return results
