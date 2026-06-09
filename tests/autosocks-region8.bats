#!/usr/bin/env bats
# AutoSOCKS Region 8 回归测试
# 验证：config_load 白名单、log 无重复、cmd_restart 无覆盖、值校验、新命令路由

setup() {
    export SCRIPT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
    export SCRIPT="$SCRIPT_DIR/autosocks"
    export TEST_DIR=$(mktemp -d)
    export LOG_FILE="$TEST_DIR/test.log"
    export PASS_FILE="$TEST_DIR/.pass"
    export PASS_SALT_FILE="$TEST_DIR/.salt"
    export PID_DIR="$TEST_DIR/run"
    export AUTOSOCKS_PROFILES_DIR="$TEST_DIR/profiles"
    mkdir -p "$PID_DIR" "$AUTOSOCKS_PROFILES_DIR"

    # 加载脚本函数（移除 main "$@" 避免自动执行）
    source <(sed '/^main "\$@"/d' "$SCRIPT" 2>/dev/null) 2>/dev/null || true

    # source 后覆盖脚本内部硬编码的默认值
    CONFIG_FILE="$TEST_DIR/config.conf"
    LOG_FILE="$TEST_DIR/test.log"
    PASS_FILE="$TEST_DIR/.pass"
    PASS_SALT_FILE="$TEST_DIR/.salt"
    PID_DIR="$TEST_DIR/run"
    AUTOSOCKS_PROFILES_DIR="$TEST_DIR/profiles"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ============================================================
# Critical #3: config_load 白名单包含 Region 8 新增 key
# ============================================================

@test "config_load: 加载包含 REMOTE_HTTP_PORT 的配置" {
    cat > "$CONFIG_FILE" << 'EOF'
SERVER_HOST="1.2.3.4"
SERVER_USER="root"
REMOTE_HTTP_PORT="8080"
HTTP_PROXY_PORT="8888"
CHECK_INTERVAL="30"
MAX_FAIL="3"
MAX_RETRY="5"
CHECK_URL="https://example.com"
LOG_MAX_SIZE="2097152"
EOF

    config_load
    [ "$?" = "0" ]
    [ "$REMOTE_HTTP_PORT" = "8080" ]
    [ "$HTTP_PROXY_PORT" = "8888" ]
    [ "$CHECK_INTERVAL" = "30" ]
    [ "$MAX_FAIL" = "3" ]
}

@test "config_load: 拒绝不在白名单中的危险 key" {
    cat > "$CONFIG_FILE" << 'EOF'
SERVER_HOST="1.2.3.4"
MALICIOUS_INJECT="rm -rf /"
EOF

    run config_load
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "无效配置项"
}

@test "config_load: FINGERPRINT_PIN 和 WEBHOOK_URL 被白名单接受" {
    cat > "$CONFIG_FILE" << 'EOF'
SERVER_HOST="1.2.3.4"
FINGERPRINT_PIN="SHA256:abc123"
WEBHOOK_URL="https://hooks.example.com/test"
EOF

    config_load
    [ "$?" = "0" ]
    [ "$FINGERPRINT_PIN" = "SHA256:abc123" ]
    [ "$WEBHOOK_URL" = "https://hooks.example.com/test" ]
}

# ============================================================
# Critical #2: log 函数写入日志文件（含轮转调用）
# ============================================================

@test "log: 写入日志文件" {
    LOG_ENABLED="true"
    log "INFO" "test" "hello world"
    [ -f "$LOG_FILE" ]
    grep -q "hello world" "$LOG_FILE"
    grep -q "\[INFO\]" "$LOG_FILE"
}

@test "log: DEBUG 级别在非调试模式下不写入" {
    LOG_ENABLED="true"
    AUTOSOCKS_DEBUG=""
    log "DEBUG" "test" "debug msg"
    [ ! -f "$LOG_FILE" ] || ! grep -q "debug msg" "$LOG_FILE"
}

# ============================================================
# Critical #1: cmd_restart 使用原始完整版本（非简化版）
# ============================================================

@test "cmd_restart: 定义中包含完整错误处理" {
    local func_body
    func_body=$(type cmd_restart 2>/dev/null)
    echo "$func_body" | grep -q "重启失败"
}

# ============================================================
# High #1: --log 命令路由
# ============================================================

@test "parse_args: --log 路由到 log 命令（不报未知选项）" {
    run bash "$SCRIPT" --log 2>&1
    # 未安装时应该报告日志文件不存在（而非"未知选项"）
    echo "$output" | grep -q "日志文件不存在"
}

# ============================================================
# High #2: restart 命令需要安装检查
# ============================================================

@test "main: restart 在未安装时提示安装" {
    run bash "$SCRIPT" restart 2>&1
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "未安装"
}

# ============================================================
# High #3: list_tunnels JSON 模式输出完整数组
# ============================================================

@test "list_tunnels: JSON 模式以 [ 开头" {
    LIST_TUNNELS_JSON="1"
    PID_DIR="$TEST_DIR/run"
    run list_tunnels
    echo "$output" | grep -q '^\['
}

# ============================================================
# 值校验 _validate_config_value（用 run 包装捕获非零退出）
# ============================================================

@test "_validate_config_value: 合法端口通过" {
    run _validate_config_value "SERVER_PORT" "80"
    [ "$status" = "0" ]
}

@test "_validate_config_value: 端口 0 被拒绝" {
    run _validate_config_value "SERVER_PORT" "0"
    [ "$status" -ne 0 ]
}

@test "_validate_config_value: 端口 70000 被拒绝" {
    run _validate_config_value "SERVER_PORT" "70000"
    [ "$status" -ne 0 ]
}

@test "_validate_config_value: 非数字端口被拒绝" {
    run _validate_config_value "LOCAL_PORT" "abc"
    [ "$status" -ne 0 ]
}

@test "_validate_config_value: AUTH_TYPE key 通过" {
    run _validate_config_value "AUTH_TYPE" "key"
    [ "$status" = "0" ]
}

@test "_validate_config_value: AUTH_TYPE invalid 被拒绝" {
    run _validate_config_value "AUTH_TYPE" "invalid"
    [ "$status" -ne 0 ]
}

@test "_validate_config_value: AUTH_KEY_PATH 路径遍历被拒绝" {
    run _validate_config_value "AUTH_KEY_PATH" "../../../etc/passwd"
    [ "$status" -ne 0 ]
}

@test "_validate_config_value: AUTH_KEY_PATH 合法路径通过" {
    run _validate_config_value "AUTH_KEY_PATH" "/home/user/.ssh/id_rsa"
    [ "$status" = "0" ]
}

@test "_validate_config_value: LOCAL_BIND 127.0.0.1 通过" {
    run _validate_config_value "LOCAL_BIND" "127.0.0.1"
    [ "$status" = "0" ]
}

@test "_validate_config_value: LOCAL_BIND 10.0.0.1 被拒绝" {
    run _validate_config_value "LOCAL_BIND" "10.0.0.1"
    [ "$status" -ne 0 ]
}

# ============================================================
# 基础设施函数
# ============================================================

@test "_read_pid_file: 读取有效 PID" {
    echo "12345" > "$TEST_DIR/test.pid"
    local pid
    pid=$(_read_pid_file "$TEST_DIR/test.pid")
    [ "$pid" = "12345" ]
}

@test "_read_pid_file: 空文件返回空" {
    : > "$TEST_DIR/test.pid"
    local pid
    pid=$(_read_pid_file "$TEST_DIR/test.pid")
    [ -z "$pid" ]
}

@test "is_pid_alive: PID 1 总是存活" {
    is_pid_alive 1
}

@test "is_pid_alive: 无效 PID 返回失败" {
    run is_pid_alive 0
    [ "$status" -ne 0 ]
}

# ============================================================
# 密码加密/解密
# ============================================================

@test "save_password + _load_password_into_memory: 加密后可解密" {
    PASS_FILE="$TEST_DIR/.pass"
    PASS_SALT_FILE="$TEST_DIR/.salt"

    save_password "my_secret_pass_123"
    [ -f "$PASS_FILE" ]

    SSH_PASSWORD=""
    _load_password_into_memory
    [ "$SSH_PASSWORD" = "my_secret_pass_123" ]
}

@test "save_password: 空密码删除文件" {
    PASS_FILE="$TEST_DIR/.pass"
    echo "old" > "$PASS_FILE"

    save_password ""
    [ ! -f "$PASS_FILE" ]
}

# ============================================================
# 日志轮转
# ============================================================

@test "rotate_log: 大文件触发轮转" {
    LOG_FILE="$TEST_DIR/test.log"
    LOG_MAX_SIZE="100"

    head -c 200 /dev/urandom > "$LOG_FILE"

    rotate_log
    [ -f "${LOG_FILE}.1" ]
    [ -f "$LOG_FILE" ]
    local size
    size=$(wc -c < "$LOG_FILE")
    [ "$size" -lt 10 ]
}

# ============================================================
# 多 profile
# ============================================================

@test "_switch_profile: 切换到指定 profile" {
    AUTOSOCKS_PROFILES_DIR="$TEST_DIR/profiles"
    CONFIG_FILE="/etc/autosocks/config.conf"

    _switch_profile "work"
    [ "$CONFIG_FILE" = "$TEST_DIR/profiles/work.conf" ]
    [ "$PASS_FILE" = "$TEST_DIR/profiles/work.pass" ]
}

@test "_switch_profile: 空名恢复默认路径" {
    _switch_profile ""
    [ "$CONFIG_FILE" = "/etc/autosocks/config.conf" ]
}

@test "_switch_profile: 拒绝非法字符" {
    run _switch_profile "../../../etc/passwd"
    [ "$status" -ne 0 ]
}

# ============================================================
# Webhook JSON 转义
# ============================================================

@test "_json_escape: 转义双引号和反斜杠" {
    local result
    result=$(_json_escape 'hello "world"')
    echo "$result" | grep -qF 'hello \"world\"'
}

# ============================================================
# 命令路由验证（通过 bash 调用脚本）
# ============================================================

@test "CLI: --doctor 正常运行" {
    run bash "$SCRIPT" --doctor 2>&1
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
    echo "$output" | grep -q "诊断报告"
}

@test "CLI: --tunnels 正常运行" {
    run bash "$SCRIPT" --tunnels 2>&1
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "NAME" || echo "$output" | grep -q "无活跃代理"
}

@test "CLI: --gen-completions 输出补全脚本" {
    run bash "$SCRIPT" --gen-completions 2>&1
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "_autosocks_completions"
}

@test "CLI: --list-profiles 正常运行" {
    run bash "$SCRIPT" --list-profiles 2>&1
    [ "$status" -eq 0 ]
}

@test "CLI: --validate-config 在未安装时不崩溃" {
    run bash "$SCRIPT" --validate-config 2>&1
    # 未安装时应该失败但不应崩溃（输出包含验证或未安装）
    echo "$output" | grep -qi "配置验证\|未安装\|不存在\|失败"
}

@test "CLI: --version 显示版本号" {
    run bash "$SCRIPT" --version 2>&1
    # 允许非零退出码（日志写入可能失败），但输出应包含版本
    echo "$output" | grep -q "v[0-9]"
}

@test "CLI: 未知选项显示帮助" {
    run bash "$SCRIPT" --unknown-option 2>&1
    [ "$status" -eq 2 ]
    echo "$output" | grep -q "未知选项"
}

@test "CLI: --profile 切换后命令仍可解析" {
    run bash "$SCRIPT" --profile test --list-profiles 2>&1
    [ "$status" -eq 0 ]
}

# ============================================================
# 区域9：借鉴 clash-for-linux-master 的新功能
# ============================================================

@test "9.1: servers list 无服务器时不崩溃" {
    SERVERS_FILE="$TEST_DIR/servers.conf"
    run bash "$SCRIPT" servers list 2>&1
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "无备用服务器"
}

@test "9.1: servers add 添加服务器" {
    SERVERS_FILE="$TEST_DIR/servers.conf"
    run bash "$SCRIPT" servers add root@1.2.3.4 22 100 test-server 2>&1
    echo "$output" | grep -q "服务器已添加" || echo "$output" | grep -q "添加"
}

@test "9.2: server_select_best 选择最高优先级" {
    SERVERS_FILE="$TEST_DIR/servers.conf"
    cat > "$SERVERS_FILE" << 'EOF'
backup1|root|5.6.7.8|22|200|0|0
primary|root|1.2.3.4|22|50|0|0
backup2|root|9.10.11.12|22|100|0|0
EOF

    local best
    best=$(server_select_best)
    echo "$best" | grep -q "1.2.3.4"
}

@test "9.2: server_select_best 跳过失败过多的" {
    SERVERS_FILE="$TEST_DIR/servers.conf"
    local now
    now=$(date +%s)
    # primary 失败 6 次，应被跳过
    cat > "$SERVERS_FILE" << EOF
primary|root|1.2.3.4|22|50|6|0
backup|root|5.6.7.8|22|200|0|0
EOF

    local best
    best=$(server_select_best)
    echo "$best" | grep -q "5.6.7.8"
}

@test "9.2: server_mark_fail 增加失败计数" {
    SERVERS_FILE="$TEST_DIR/servers.conf"
    echo "test|root|1.2.3.4|22|100|2|0" > "$SERVERS_FILE"

    server_mark_fail "1.2.3.4"
    local fails
    fails=$(awk -F'|' '$1=="test"{print $6}' "$SERVERS_FILE")
    [ "$fails" = "3" ]
}

@test "9.2: server_reset_fails 重置计数" {
    SERVERS_FILE="$TEST_DIR/servers.conf"
    echo "test|root|1.2.3.4|22|100|5|12345" > "$SERVERS_FILE"

    server_reset_fails "1.2.3.4"
    local fails
    fails=$(awk -F'|' '$1=="test"{print $6}' "$SERVERS_FILE")
    [ "$fails" = "0" ]
}

@test "9.3: health status 未启动时报告" {
    HEALTH_CHECK_PID_FILE="$TEST_DIR/health.pid"
    run bash "$SCRIPT" health status 2>&1
    echo "$output" | grep -q "未启动\|未运行"
}

@test "9.4: resolve_available_port 返回空闲端口" {
    # 1080 通常不被占用（非 root 环境）
    local port
    port=$(resolve_available_port 10800 10801 10900)
    [ -n "$port" ]
}

@test "9.5: _inject_marker_block 幂等注入" {
    local test_file="$TEST_DIR/test_rc"
    echo "# existing content" > "$test_file"

    _inject_marker_block "$test_file" 'eval "$(autosocks env)"'

    # 验证标记块存在
    grep -q "# >>> autosocks >>>" "$test_file"
    grep -q "# <<< autosocks <<<" "$test_file"
    grep -q "autosocks env" "$test_file"
    # 验证原有内容保留
    grep -q "existing content" "$test_file"
}

@test "9.5: _inject_marker_block 重复注入幂等" {
    local test_file="$TEST_DIR/test_rc"
    echo "# original" > "$test_file"

    _inject_marker_block "$test_file" 'eval "$(autosocks env)"'
    _inject_marker_block "$test_file" 'eval "$(autosocks env)"'

    # 标记块只出现一次
    local count
    count=$(grep -c "# >>> autosocks >>>" "$test_file")
    [ "$count" -eq 1 ]
}

@test "9.5: _remove_marker_block 清除标记块" {
    local test_file="$TEST_DIR/test_rc"
    echo "# original" > "$test_file"
    _inject_marker_block "$test_file" 'eval "$(autosocks env)"'

    _remove_marker_block "$test_file"

    # 标记块应被移除
    ! grep -q "# >>> autosocks >>>" "$test_file"
    # 原有内容保留
    grep -q "original" "$test_file"
}

@test "9.6: autosocks_mktemp 创建临时文件" {
    local tmp
    tmp=$(autosocks_mktemp "test")
    [ -n "$tmp" ]
    touch "$tmp" 2>/dev/null
    rm -f "$tmp"
}

@test "9.6: config_checksum 计算校验和" {
    echo "test content" > "$CONFIG_FILE"
    local sum
    sum=$(config_checksum)
    [ -n "$sum" ]
    [ "${#sum}" -eq "64" ]  # SHA256 hex = 64 chars
}

@test "9.6: config_checksum_verify 检测篡改" {
    echo "original" > "$CONFIG_FILE"
    config_checksum_save

    # 未修改 → 通过
    config_checksum_verify

    # 修改后 → 失败
    echo "modified" > "$CONFIG_FILE"
    run config_checksum_verify
    [ "$status" -ne 0 ]
}

@test "9.6: _push_trap 堆栈存储回调" {
    _push_trap EXIT "echo test_trap_1"
    _push_trap EXIT "echo test_trap_2"
    [ "${#_AUTOSOCKS_TRAP_STACK_EXIT[@]}" -ge 2 ]
}

@test "CLI: servers 子命令路由正确" {
    run bash "$SCRIPT" servers list 2>&1
    [ "$status" -eq 0 ]
}

@test "CLI: health 子命令路由正确" {
    run bash "$SCRIPT" health status 2>&1
    echo "$output" | grep -qi "health\|健康\|未启动\|未运行\|守护"
}

@test "CLI: --self-update 路由正确" {
    run bash "$SCRIPT" --self-update 2>&1
    # 可能因网络失败，但不应是"未知选项"
    ! echo "$output" | grep -q "未知选项"
}

@test "CLI: --reconfigure 需要安装检查" {
    run bash "$SCRIPT" --reconfigure 2>&1
    echo "$output" | grep -q "未安装\|root\|权限"
}
