"""config.py 测试 - 配置加载、保存、校验"""
import textwrap
from pathlib import Path

from autosocks.core.config import load_config, save_config, validate_config, ConfigError, DEFAULTS


class TestLoadConfig:
    """测试从 INI 文件加载配置"""

    def test_load_valid_config(self, tmp_path: Path):
        """从有效的 INI 文件加载配置，返回正确的值"""
        config_file = tmp_path / "config.conf"
        config_file.write_text(textwrap.dedent("""\
            [server]
            host = 1.2.3.4
            user = root
            port = 22

            [local]
            port = 1080
            bind = 127.0.0.1

            [auth]
            type = key
            key_path = ~/.ssh/id_rsa

            [ssh]
            keepalive = 60
            timeout = 10

            [reconnect]
            enabled = true
            interval = 3

            [log]
            enabled = true
            max_size = 1048576
        """))

        config = load_config(config_file)

        assert config["server_host"] == "1.2.3.4"
        assert config["server_user"] == "root"
        assert config["server_port"] == 22
        assert config["local_port"] == 1080
        assert config["local_bind"] == "127.0.0.1"
        assert config["auth_type"] == "key"
        assert config["auth_key_path"] == "~/.ssh/id_rsa"
        assert config["reconnect_enabled"] is True
        assert config["log_enabled"] is True

    def test_load_missing_file_returns_defaults(self, tmp_path: Path):
        """配置文件不存在时返回全部默认值"""
        config = load_config(tmp_path / "nonexistent.conf")

        assert config == DEFAULTS


class TestSaveConfig:
    """测试保存配置到 INI 文件"""

    def test_save_and_reload_roundtrip(self, tmp_path: Path):
        """保存配置后再加载，值一致"""
        config_file = tmp_path / "config.conf"
        config = {
            "server_host": "5.6.7.8",
            "server_user": "admin",
            "server_port": 2222,
            "local_port": 1081,
            "local_bind": "0.0.0.0",
            "auth_type": "key",
            "auth_key_path": "~/.ssh/my_key",
            "auth_password": "",
            "ssh_keepalive": 120,
            "ssh_timeout": 15,
            "reconnect_enabled": False,
            "reconnect_interval": 5,
            "log_enabled": False,
            "log_max_size": 2097152,
        }

        save_config(config_file, config)
        loaded = load_config(config_file)

        assert loaded == config

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        """保存配置时自动创建父目录"""
        config_file = tmp_path / "deep" / "nested" / "config.conf"
        save_config(config_file, {"server_host": "1.2.3.4"})

        assert config_file.exists()


class TestValidateConfig:
    """测试配置校验"""

    def test_valid_config_passes(self):
        """有效配置校验通过"""
        config = dict(DEFAULTS)
        config["server_host"] = "1.2.3.4"
        # 不应抛异常
        validate_config(config)

    def test_empty_server_host_fails(self):
        """server_host 为空时校验失败"""
        config = dict(DEFAULTS)
        config["server_host"] = ""

        try:
            validate_config(config)
            assert False, "应该抛出 ConfigError"
        except ConfigError as e:
            assert "server_host" in str(e)

    def test_invalid_port_fails(self):
        """端口超出范围时校验失败"""
        config = dict(DEFAULTS)
        config["server_host"] = "1.2.3.4"
        config["local_port"] = 99999

        try:
            validate_config(config)
            assert False, "应该抛出 ConfigError"
        except ConfigError as e:
            assert "local_port" in str(e)

    def test_invalid_auth_type_fails(self):
        """无效的 auth_type 校验失败"""
        config = dict(DEFAULTS)
        config["server_host"] = "1.2.3.4"
        config["auth_type"] = "invalid"

        try:
            validate_config(config)
            assert False, "应该抛出 ConfigError"
        except ConfigError as e:
            assert "auth_type" in str(e)
