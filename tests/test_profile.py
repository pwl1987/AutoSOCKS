"""plugins/profile.py 测试 - 多 Profile 管理"""
from pathlib import Path
from autosocks.plugins.profile import list_profiles, create_profile, delete_profile


class TestListProfiles:
    """测试列出 profiles"""

    def test_list_empty(self, tmp_path: Path):
        """无 profile 返回空列表"""
        profiles = list_profiles(tmp_path)
        assert profiles == []

    def test_list_existing(self, tmp_path: Path):
        """列出已有 profiles"""
        (tmp_path / "work.conf").write_text("[server]\nhost = 1.2.3.4\n")
        (tmp_path / "home.conf").write_text("[server]\nhost = 5.6.7.8\n")
        profiles = list_profiles(tmp_path)
        assert "work" in profiles
        assert "home" in profiles

    def test_list_ignores_non_conf(self, tmp_path: Path):
        """忽略非 .conf 文件"""
        (tmp_path / "readme.txt").write_text("hello")
        profiles = list_profiles(tmp_path)
        assert profiles == []


class TestCreateProfile:
    """测试创建 profile"""

    def test_create_success(self, tmp_path: Path):
        """创建 profile 文件"""
        result = create_profile(tmp_path / "test.conf", {"server_host": "1.2.3.4"})
        assert result is True
        assert (tmp_path / "test.conf").exists()

    def test_create_creates_dir(self, tmp_path: Path):
        """自动创建目录"""
        target = tmp_path / "deep" / "test.conf"
        result = create_profile(target, {"server_host": "1.2.3.4"})
        assert result is True


class TestDeleteProfile:
    """测试删除 profile"""

    def test_delete_existing(self, tmp_path: Path):
        """删除已有 profile"""
        p = tmp_path / "test.conf"
        p.write_text("[server]\nhost = 1.2.3.4\n")
        result = delete_profile(p)
        assert result is True
        assert not p.exists()

    def test_delete_nonexistent(self, tmp_path: Path):
        """删除不存在的 profile"""
        result = delete_profile(tmp_path / "nope.conf")
        assert result is False
