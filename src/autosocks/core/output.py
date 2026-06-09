"""终端输出工具 - 颜色、图标、格式化"""
from __future__ import annotations

import os
import sys


# ANSI 颜色代码
_RED = "\033[0;31m"
_GREEN = "\033[0;32m"
_YELLOW = "\033[0;33m"
_BLUE = "\033[0;34m"
_NC = "\033[0m"

# 运行时颜色状态（可被 NO_COLOR 或非 TTY 禁用）
_RED_ON = _RED
_GREEN_ON = _GREEN
_YELLOW_ON = _YELLOW
_BLUE_ON = _BLUE
_NC_ON = _NC


def _init_colors() -> None:
    """根据环境初始化颜色开关。NO_COLOR=1 或非 TTY 时禁用颜色。"""
    global _RED_ON, _GREEN_ON, _YELLOW_ON, _BLUE_ON, _NC_ON

    if os.environ.get("NO_COLOR") == "1" or not sys.stdout.isatty():
        _RED_ON = ""
        _GREEN_ON = ""
        _YELLOW_ON = ""
        _BLUE_ON = ""
        _NC_ON = ""
    else:
        _RED_ON = _RED
        _GREEN_ON = _GREEN
        _YELLOW_ON = _YELLOW
        _BLUE_ON = _BLUE
        _NC_ON = _NC


# 模块加载时初始化
_init_colors()


def print_success(message: str) -> None:
    """输出成功信息（绿色勾号）"""
    print(f"{_GREEN_ON}✅ {message}{_NC_ON}")


def print_error(message: str, error_code: str = "") -> None:
    """输出错误信息（红色叉号，到 stderr）"""
    if error_code:
        print(f"{_RED_ON}❌ {message} [错误码：{error_code}]{_NC_ON}", file=sys.stderr)
    else:
        print(f"{_RED_ON}❌ {message}{_NC_ON}", file=sys.stderr)


def print_warning(message: str) -> None:
    """输出警告信息（黄色）"""
    print(f"{_YELLOW_ON}⚠️  {message}{_NC_ON}")


def print_info(message: str) -> None:
    """输出提示信息（蓝色）"""
    print(f"{_BLUE_ON}💡 {message}{_NC_ON}")
