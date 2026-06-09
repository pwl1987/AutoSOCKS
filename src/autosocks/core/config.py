"""配置管理 - INI 格式配置文件加载、保存、校验"""
from __future__ import annotations

import configparser
from pathlib import Path


class ConfigError(Exception):
    """配置校验错误"""


# 合法的 auth_type 值
_VALID_AUTH_TYPES = {"key", "password"}

# 端口合法范围
_PORT_RANGE = (1, 65535)


# 默认配置值
DEFAULTS: dict[str, object] = {
    "server_host": "",
    "server_user": "root",
    "server_port": 22,
    "local_port": 1080,
    "local_bind": "127.0.0.1",
    "auth_type": "key",
    "auth_key_path": "",
    "ssh_keepalive": 60,
    "ssh_timeout": 10,
    "reconnect_enabled": True,
    "reconnect_interval": 3,
    "log_enabled": True,
    "log_max_size": 1048576,
}

# INI section → (ini_key, config_key, type) 映射
_SECTION_MAP: dict[str, list[tuple[str, str, type]]] = {
    "server": [
        ("host", "server_host", str),
        ("user", "server_user", str),
        ("port", "server_port", int),
    ],
    "local": [
        ("port", "local_port", int),
        ("bind", "local_bind", str),
    ],
    "auth": [
        ("type", "auth_type", str),
        ("key_path", "auth_key_path", str),
    ],
    "ssh": [
        ("keepalive", "ssh_keepalive", int),
        ("timeout", "ssh_timeout", int),
    ],
    "reconnect": [
        ("enabled", "reconnect_enabled", bool),
        ("interval", "reconnect_interval", int),
    ],
    "log": [
        ("enabled", "log_enabled", bool),
        ("max_size", "log_max_size", int),
    ],
}


def load_config(path: Path) -> dict[str, object]:
    """从 INI 文件加载配置，返回扁平化的配置字典。

    Args:
        path: INI 配置文件路径

    Returns:
        配置字典，key 为扁平化名称（如 server_host），value 为对应类型
    """
    config = dict(DEFAULTS)

    parser = configparser.ConfigParser()
    parser.read(str(path))

    for section, keys in _SECTION_MAP.items():
        if not parser.has_section(section):
            continue
        for ini_key, config_key, value_type in keys:
            raw = parser.get(section, ini_key)
            if value_type is bool:
                config[config_key] = raw.lower() in ("true", "yes", "1", "on")
            elif value_type is int:
                config[config_key] = int(raw)
            else:
                config[config_key] = raw

    return config


def save_config(path: Path, config: dict[str, object]) -> None:
    """将配置字典保存为 INI 文件。

    Args:
        path: 目标 INI 文件路径
        config: 配置字典（只需包含要覆盖的 key，其余用默认值填充）
    """
    merged = dict(DEFAULTS)
    merged.update(config)

    parser = configparser.ConfigParser()

    for section, keys in _SECTION_MAP.items():
        parser.add_section(section)
        for ini_key, config_key, _value_type in keys:
            value = merged[config_key]
            if isinstance(value, bool):
                parser.set(section, ini_key, "true" if value else "false")
            else:
                parser.set(section, ini_key, str(value))

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        parser.write(f)


def validate_config(config: dict[str, object]) -> None:
    """校验配置值，不合法时抛出 ConfigError。

    Args:
        config: 配置字典

    Raises:
        ConfigError: 配置值不合法
    """
    errors: list[str] = []

    # server_host 不能为空
    if not config.get("server_host"):
        errors.append("server_host 不能为空")

    # 端口范围校验
    for port_key in ("server_port", "local_port"):
        port = config.get(port_key, 0)
        if not isinstance(port, int) or not (_PORT_RANGE[0] <= port <= _PORT_RANGE[1]):
            errors.append(f"{port_key} 必须在 {_PORT_RANGE[0]}-{_PORT_RANGE[1]} 之间")

    # auth_type 校验
    auth_type = config.get("auth_type", "")
    if auth_type not in _VALID_AUTH_TYPES:
        errors.append(f"auth_type 必须是 {', '.join(_VALID_AUTH_TYPES)} 之一")

    if errors:
        raise ConfigError("; ".join(errors))
