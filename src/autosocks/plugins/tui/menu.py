"""TUI L2 交互式菜单 - 选择、输入"""
from __future__ import annotations

import sys


def select_option(prompt: str, options: list[str], default: int = 0) -> int:
    """交互式选择菜单。

    Args:
        prompt: 提示文字
        options: 选项列表
        default: 默认选项索引（空输入时使用）

    Returns:
        选择的选项索引（0-based）
    """
    while True:
        print(f"\n{prompt}")
        for i, opt in enumerate(options, 1):
            marker = " →" if i - 1 == default else "  "
            print(f"{marker} {i}. {opt}")
        print()

        try:
            choice = input(f"请选择 [1-{len(options)}]（默认 {default + 1}）: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(1)

        if not choice:
            return default

        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1

        print(f"  无效输入，请输入 1-{len(options)} 之间的数字")


def input_text(prompt: str, default: str = "", required: bool = False) -> str:
    """交互式文本输入。

    Args:
        prompt: 提示文字
        default: 默认值
        required: 是否必填

    Returns:
        输入的文本
    """
    while True:
        hint = f"（默认: {default}）" if default else ""
        try:
            value = input(f"{prompt}{hint}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(1)

        if not value:
            if default:
                return default
            if not required:
                return ""
            print("  此项为必填，请重新输入")
            continue

        return value
