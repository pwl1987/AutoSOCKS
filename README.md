# AutoSOCKS v1.0.0

极简 Linux SSH SOCKS5 代理管理工具。

## 功能特性

- **一键安装**：交互式安装向导，自动配置 systemd 服务
- **SOCKS5 代理**：基于 SSH -D 动态端口转发
- **HTTP 代理**：支持 Privoxy 和 gost 双引擎 SOCKS5→HTTP 转换
- **服务管理**：systemd 守护进程，开机自启，自动重连
- **多服务器故障转移**：备用服务器优先级排序，自动切换
- **健康检查守护**：持续监控 + 指数退避 + 自动重连
- **自更新机制**：GitHub 镜像池 + 评分排序 + 冷却机制
- **交互式重配置**：端口冲突自动解决
- **GeoIP 分流**：基于 DB-IP 数据库的国内外流量分流
- **密码加密存储**：AES-256-CBC + PBKDF2
- **Webhook 告警**：队列重试机制
- **多 Profile 支持**：`~/.autosocks.d/` 多配置管理
- **Bash 补全**：Tab 自动补全
- **一键自检**：`autosocks --doctor` 诊断报告

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/pwl1987/AutoSOCKS.git
cd AutoSOCKS

# 安装到系统
sudo bash autosocks install
```

### 常用命令

```bash
autosocks status          # 查看状态
autosocks start           # 启动代理
autosocks stop            # 停止代理
autosocks restart         # 重启代理
autosocks logs            # 查看日志
autosocks --doctor        # 一键自检
autosocks config --server root@1.2.3.4  # 修改服务器
autosocks servers list    # 查看备用服务器
autosocks health status   # 健康检查守护状态
```

### 环境变量

```bash
# 自动设置代理环境变量
eval "$(autosocks env)"

# 取消代理
eval "$(autosocks env unset)"
```

## 项目结构

```
AutoSOCKS/
├── autosocks              # 主脚本（单文件，~9000行）
├── tests/
│   ├── autosocks-region8.bats   # 核心回归测试
│   ├── config.bats              # 配置加载测试
│   ├── security.bats            # 安全测试
│   └── ...
├── .gitignore
└── README.md
```

## 系统要求

- Linux（支持 systemd）
- Bash 4.0+
- SSH 客户端
- curl

### 可选依赖

- `autossh`：自动重连（推荐）
- `sshpass`：密码认证
- `gost`：HTTP 代理（SOCKS5→HTTP 转换）
- `privoxy`：HTTP 代理（备选方案）
- `iptables` + `ipset`：GeoIP 分流

## 配置

配置文件位于 `/etc/autosocks/config.conf`：

```bash
SERVER_HOST="your-server.com"
SERVER_USER="root"
SERVER_PORT="22"
LOCAL_PORT="1080"
AUTH_TYPE="key"              # key 或 password
SSH_KEEPALIVE="60"
CHECK_INTERVAL="30"
MAX_FAIL="3"
```

## 许可证

MIT License
