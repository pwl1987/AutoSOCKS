# AutoSOCKS v2.0.0

极简 Linux SSH SOCKS5 代理管理工具，Python 重写版。

## 功能特性

- **一行安装**：`curl | bash` 安装体验，自动检测 Python 环境
- **本地安装**：`--local` 从本地源码安装，无需网络
- **交互式配置**：`autosocks install` TUI 向导式配置服务器
- **TUI 界面**：`autosocks tui` 双栏布局全屏 curses 交互界面
- **后台运行**：TUI 关闭后代理服务持续运行（systemd 管理）
- **SOCKS5 代理**：基于 SSH `-D` 动态端口转发
- **HTTP 代理**：支持 gost SOCKS5→HTTP 转换（可选 Privoxy）
- **服务管理**：systemd 守护进程，开机自启，自动重连
- **健康检查**：服务状态 + 代理可用性 + 延迟采样
- **GeoIP 分流**：基于 CIDR IP 列表的国内外流量分流
- **多 Profile**：多服务器配置管理（创建/切换/删除）
- **Webhook 告警**：JSON POST 推送到外部服务
- **Shell 集成**：`eval $(autosocks env)` 自动设置代理环境变量
- **自更新**：检查 GitHub 最新版本，一键升级
- **零依赖**：纯 Python 标准库，无第三方运行时依赖

## 快速开始

### 安装

```bash
# 远程安装（推荐）
curl -fsSL https://raw.githubusercontent.com/pwl1987/AutoSOCKS/main/install.sh | sudo bash

# 本地安装（从源码目录）
git clone https://github.com/pwl1987/AutoSOCKS.git
cd AutoSOCKS
sudo bash install.sh --local

# 指定服务器地址
curl -fsSL https://raw.githubusercontent.com/pwl1987/AutoSOCKS/main/install.sh | sudo bash -s -- --server root@1.2.3.4
```

### 配置

```bash
# 交互式配置服务器（TUI 面板 + 选择菜单）
sudo autosocks install
```

### 常用命令

```bash
autosocks install             # TUI 交互式配置
autosocks start               # 启动代理
autosocks stop                # 停止代理
autosocks restart             # 重启代理
autosocks status              # 查看状态
autosocks env                 # 设置代理环境变量
autosocks tui                 # TUI 全屏交互界面
autosocks version             # 显示版本
autosocks help                # 查看帮助
```

### 环境变量

```bash
# 自动设置代理环境变量
eval "$(autosocks env)"

# 添加到 ~/.bashrc 实现自动设置
echo 'eval "$(autosocks env 2>/dev/null)"' >> ~/.bashrc

# 取消代理
eval "$(autosocks env unset)"
```

### 卸载

```bash
sudo bash install.sh --uninstall
# 询问是否保留配置文件（/etc/autosocks/）
```

## 手册

### 命令详解

#### `autosocks install`

TUI 交互式配置向导，引导你完成服务器配置。

```bash
sudo autosocks install
```

配置流程：
1. 输入服务器地址（格式：`user@host[:port]`，支持 IPv6）
2. 输入本地 SOCKS5 端口（默认 1080）
3. 输入绑定地址（默认 127.0.0.1）
4. 选择认证方式（SSH 密钥 / 密码认证）
5. 配置心跳间隔、连接超时
6. 配置自动重连
7. 配置日志
8. 预览配置，确认保存

#### `autosocks start`

启动 SOCKS5 代理服务（systemd）。

```bash
sudo autosocks start
```

前提：已通过 `autosocks install` 完成配置。

#### `autosocks stop`

停止代理服务。

```bash
sudo autosocks stop
```

#### `autosocks restart`

重启代理服务（修改配置后使用）。

```bash
sudo autosocks restart
```

#### `autosocks status`

查看代理服务运行状态和配置信息。

```bash
sudo autosocks status
```

#### `autosocks env`

输出 shell 环境变量设置命令。用于让终端应用走代理。

```bash
# 设置代理（http_proxy, https_proxy, ALL_PROXY 等）
eval "$(autosocks env)"

# 取消代理
eval "$(autosocks env unset)"
```

设置的环境变量：
- `http_proxy` / `https_proxy`
- `HTTP_PROXY` / `HTTPS_PROXY`
- `all_proxy` / `ALL_PROXY`
- `no_proxy` / `NO_PROXY`
- `socks_proxy` / `SOCKS_PROXY`
- `ftp_proxy` / `FTP_PROXY`

#### `autosocks tui`

启动全屏 TUI 交互界面（curses 双栏布局）。

```bash
sudo autosocks tui
```

**界面布局**：左侧菜单栏 + 右侧实时状态面板

**快捷键**：

| 快捷键 | 功能 |
|--------|------|
| `↑/↓` 或 `j/k` | 移动选择 |
| `Enter` | 执行操作 |
| `PgUp/PgDn` | 翻页 |
| `s` | 启动代理 |
| `S` | 停止代理 |
| `r` | 重启代理 |
| `i` | 查看状态 |
| `h` | 健康检查 |
| `d` | 后台运行（关闭 TUI，代理继续运行） |
| `q` | 退出 |

**菜单分组（6 组 27 项）**：

| 分组 | 菜单项 |
|------|--------|
| 代理管理 | 启动/停止/重启代理、运行状态、健康检查、延迟测试 |
| 代理工具 | HTTP 代理转发、环境变量、Shell 集成 |
| 配置编辑 | 配置向导、服务器/本地端口/认证/SSH 参数/重连/日志/Webhook 告警/GeoIP 分流 |
| Profile | 查看/创建/切换/删除 Profile |
| 系统工具 | 查看完整配置、查看日志、检查更新、后台运行 |
| 退出 | 退出 TUI |

**右侧状态面板实时显示**：
- 服务运行状态（运行中/已停止）
- 延迟（ms）和出口 IP（异步后台检测）
- 服务器信息、SSH 端口、本地监听地址
- 认证方式、心跳/超时参数、重连状态
- SOCKS5/HTTP 代理地址
- 操作结果消息（成功/失败/警告，自动超时清除）

**后台运行**：
- 按 `d` 一键切换后台模式，TUI 关闭后代理服务持续运行
- 退出时自动提示后台运行状态和管理命令

#### `autosocks version`

显示版本号。

#### `autosocks help`

显示帮助信息。

### 安装器

#### 远程安装

从 GitHub 下载并安装最新版：

```bash
curl -fsSL https://raw.githubusercontent.com/pwl1987/AutoSOCKS/main/install.sh | sudo bash
```

#### 本地安装

从本地源码安装，无需网络：

```bash
git clone https://github.com/pwl1987/AutoSOCKS.git
cd AutoSOCKS
sudo bash install.sh --local
```

#### 卸载

```bash
sudo bash install.sh --uninstall
```

卸载流程：
1. 停止 autosocks 服务
2. 禁用开机自启
3. 删除 systemd unit 文件
4. 删除 `/usr/local/bin/autosocks` 启动脚本
5. 删除 `/opt/autosocks` 虚拟环境
6. 询问是否删除 `/etc/autosocks` 配置目录

### 配置文件

配置文件位于 `/etc/autosocks/config.conf`（INI 格式）：

```ini
[server]
host = your-server.com
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
```

Profile 文件位于 `/etc/autosocks/profiles/`，格式与主配置相同。

### 错误码

| 错误码 | 说明 |
|--------|------|
| E001 | 需要 root 权限 |
| E002 | 配置文件不存在 |
| E003 | 配置项缺失 |
| E004 | 配置项格式错误 |
| E005 | 配置校验失败 |
| E006 | 未配置服务器地址 |
| E007 | SSH 未安装 |
| E008 | SSH 连接失败 |
| E009 | 端口已被占用 |
| E010 | 服务启动失败 |
| E011 | 服务停止失败 |
| E012 | 未知命令 |
| E013 | 网络不可达 |
| E014 | DNS 解析失败 |

### Python API

AutoSOCKS 的所有功能都可以作为 Python 模块使用：

```python
from autosocks.core.config import load_config, save_config
from autosocks.core.tunnel import build_ssh_command, check_proxy
from autosocks.core.service import service_start, service_stop, service_is_active
from autosocks.plugins.health import check_health
from autosocks.plugins.proxy import start_http_proxy, stop_http_proxy
from autosocks.plugins.env import env_set, env_unset
from autosocks.plugins.geo import load_ip_list, is_china_ip
from autosocks.plugins.update import check_latest_version, perform_update
from autosocks.plugins.profile import create_profile, list_profiles, delete_profile
from autosocks.plugins.webhook import send_webhook
from autosocks.plugins.tui.beautify import panel, table_row, divider
from autosocks.plugins.tui.menu import select_option, input_text
from autosocks.plugins.tui.dashboard import render_dashboard, render_dashboard_plain, DashboardData
from autosocks.plugins.tui.app import TUIApp
```

## 项目结构

```
src/autosocks/
├── __init__.py
├── __main__.py
├── cli.py                      # 命令分发 (match/case)
├── core/
│   ├── config.py               # INI 配置管理
│   ├── errors.py               # 错误码 E001-E014
│   ├── output.py               # 终端输出
│   ├── service.py              # systemd 操作
│   └── tunnel.py               # SSH 隧道管理
├── plugins/
│   ├── env.py                  # 环境变量
│   ├── geo.py                  # GeoIP 分流
│   ├── health.py               # 健康检查
│   ├── profile.py              # 多 Profile 管理
│   ├── proxy.py                # HTTP 代理 (gost/privoxy)
│   ├── shell_integration.py    # Shell 集成
│   ├── update.py               # 自更新
│   ├── webhook.py              # Webhook 告警
│   └── tui/
│       ├── __init__.py         # 模块导出
│       ├── beautify.py         # L1 美化面板
│       ├── menu.py             # L2 交互式菜单
│       ├── dashboard.py        # L3 实时仪表盘（ANSI + 纯文本）
│       └── app.py              # L3 全屏 TUI (curses 双栏布局)
└── utils/
install.sh                      # Bash 安装/卸载器
```

## 系统要求

- Linux（支持 systemd）
- Python 3.10+
- SSH 客户端
- curl（远程安装时需要）

### 可选依赖

- `gost`：HTTP 代理（SOCKS5→HTTP 转换）
- `privoxy`：HTTP 代理（备选方案）

## 开发

```bash
# 设置开发环境
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 运行测试（158 tests）
pytest tests/ -v

# 代码检查
ruff check src/ tests/
mypy src/ --ignore-missing-imports
```

## 从 v1.0.0 迁移

v2.0.0 会自动将旧的 `KEY="value"` 配置转换为 INI 格式。安装时运行：

```bash
sudo bash install.sh
sudo autosocks install
```

## 许可证

MIT License
