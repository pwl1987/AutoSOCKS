#!/usr/bin/env bats
# AutoSOCKS TDD 修复验证测试
# 不依赖 setup() 中的 source，直接运行脚本和 grep

SCRIPT="${BATS_TEST_DIRNAME:-$(dirname "$BATS_TEST_FILENAME")}/../autosocks"

@test "URL: 帮助信息不含占位符 github.com/xxx" {
    run bash "$SCRIPT" help --all 2>&1
    ! echo "$output" | grep -q "github.com/xxx"
}

@test "URL: 头部注释包含正确的 GitHub 仓库地址" {
    result=$(head -10 "$SCRIPT")
    echo "$result" | grep -q "github.com/pwl1987/AutoSOCKS"
}

@test "URL: 错误提示不含占位符 URL" {
    ! grep -q 'github.com/xxx' "$SCRIPT"
}

@test "路径: CHINA_IP_LIST_FILE 不是硬编码的 /home/code 路径" {
    ! grep -q 'CHINA_IP_LIST_FILE="/home/code' "$SCRIPT"
}

@test "路径: CHINA_IP_LIST_FILE 使用可配置路径" {
    grep -q 'CHINA_IP_LIST_FILE="\${AUTOSOCKS_' "$SCRIPT" || grep -q 'CHINA_IP_LIST_FILE="\${CONFIG_DIR' "$SCRIPT"
}

@test "清理: 不存在 _main_old 残留函数" {
    ! grep -q '_main_old()' "$SCRIPT"
}

@test "shellcheck: 无 SC2034 socks_status 告警" {
    ! shellcheck -S warning "$SCRIPT" 2>&1 | grep -q 'socks_status appears unused'
}

@test "语法: bash -n 通过" {
    bash -n "$SCRIPT"
}

@test "版本: VERSION 已定义" {
    grep -q '^VERSION="[0-9]' "$SCRIPT"
}

@test "版本: README 版本号与脚本一致" {
    local script_version
    script_version=$(grep '^VERSION=' "$SCRIPT" | cut -d'"' -f2)
    local readme="${BATS_TEST_DIRNAME:-$(dirname "$BATS_TEST_FILENAME")}/../README.md"
    grep -q "v${script_version}" "$readme"
}
