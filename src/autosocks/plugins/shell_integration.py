"""Shell 集成 - 代理自动恢复脚本"""
from __future__ import annotations

from pathlib import Path


def install_integration(script_path: Path, port: int = 1080) -> None:
    """安装 Shell 集成脚本。

    Args:
        script_path: 脚本保存路径
        port: SOCKS5 端口
    """
    script_path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# AutoSOCKS Shell Integration (port: {port})
# 自动设置代理环境变量
_autosocks_env() {{
    if command -v autosocks &>/dev/null; then
        eval "$(autosocks env 2>/dev/null)"
    fi
}}

# PROMPT_COMMAND 中自动恢复代理
if [ -z "$AUTOSOCKS_INTEGRATED" ]; then
    export AUTOSOCKS_INTEGRATED=1
    _autosocks_env
fi
"""
    script_path.write_text(content)


def uninstall_integration(script_path: Path) -> None:
    """卸载 Shell 集成脚本。

    Args:
        script_path: 脚本路径
    """
    if script_path.exists():
        script_path.unlink()
