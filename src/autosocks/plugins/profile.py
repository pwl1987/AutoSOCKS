"""多 Profile 管理 - 列出、创建、删除配置 profile"""
from __future__ import annotations

from pathlib import Path


def list_profiles(profile_dir: Path) -> list[str]:
    """列出所有 profile 名称。

    Args:
        profile_dir: profile 目录

    Returns:
        profile 名称列表（不含 .conf 后缀）
    """
    if not profile_dir.exists():
        return []

    return [f.stem for f in sorted(profile_dir.glob("*.conf"))]


def create_profile(path: Path, config: dict[str, object]) -> bool:
    """创建 profile 配置文件。

    Args:
        path: profile 文件路径
        config: 配置字典

    Returns:
        True 成功
    """
    from autosocks.core.config import save_config
    try:
        save_config(path, config)
        return True
    except Exception:
        return False


def delete_profile(path: Path) -> bool:
    """删除 profile 文件。

    Args:
        path: profile 文件路径

    Returns:
        True 成功，False 文件不存在
    """
    if path.exists():
        path.unlink()
        return True
    return False
