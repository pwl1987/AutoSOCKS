"""环境变量管理 - 设置/清除代理环境变量"""
from __future__ import annotations


def env_set(bind: str, port: int) -> None:
    """输出设置代理环境变量的 shell 命令。

    用法：eval $(autosocks env)

    Args:
        bind: 绑定地址
        port: SOCKS5 端口
    """
    proxy_url = f"socks5h://{bind}:{port}"
    no_proxy = "localhost,127.0.0.1,::1"

    print(f'export http_proxy="{proxy_url}"')
    print(f'export https_proxy="{proxy_url}"')
    print(f'export HTTP_PROXY="{proxy_url}"')
    print(f'export HTTPS_PROXY="{proxy_url}"')
    print(f'export ALL_PROXY="{proxy_url}"')
    print(f'export all_proxy="{proxy_url}"')
    print(f'export no_proxy="{no_proxy}"')
    print(f'export NO_PROXY="{no_proxy}"')


def env_unset() -> None:
    """输出清除代理环境变量的 shell 命令。

    用法：eval $(autosocks env unset)
    """
    for var in (
        "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
        "ALL_PROXY", "all_proxy", "no_proxy", "NO_PROXY",
    ):
        print(f"unset {var}")
