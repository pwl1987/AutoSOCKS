"""TUI L1 美化输出 - 面板、表格行、分隔线"""
from __future__ import annotations

import os

# 终端宽度（默认 80）
def _term_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def panel(title: str, lines: list[str]) -> None:
    """输出带边框的面板。

    Args:
        title: 面板标题
        lines: 面板内容行
    """
    width = _term_width()
    inner = min(width - 4, 60)

    # 顶边框
    print(f"\033[1;32m┏{'━' * (inner + 2)}┓\033[0m")
    # 标题行
    print(f"\033[1;32m┃\033[0m \033[1m{title:^{inner}}\033[0m \033[1;32m┃\033[0m")
    # 分隔
    print(f"\033[1;32m┣{'━' * (inner + 2)}┫\033[0m")
    # 内容行
    for line in lines:
        print(f"\033[1;32m┃\033[0m {line:<{inner}} \033[1;32m┃\033[0m")
    # 底边框
    print(f"\033[1;32m┗{'━' * (inner + 2)}┛\033[0m")


def table_row(key: str, value: str) -> None:
    """输出对齐的表格行。

    Args:
        key: 键名
        value: 值
    """
    print(f"  \033[1m{key:<12}\033[0m {value}")


def divider() -> None:
    """输出分隔线。"""
    width = _term_width()
    line_len = min(width - 2, 50)
    print(f"\033[0;36m{'─' * line_len}\033[0m")
