#!/bin/bash
#
# 一键部署到 GitHub Pages
#
# 使用前:
#   1. 登录 GitHub，新建一个仓库 (建议设为 Public)
#      例如仓库名: beijing-dashboard
#   2. 把仓库地址填到下方变量
#   3. 运行本脚本
#
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# ===== 在这里填你的 GitHub 仓库地址 =====
REMOTE_URL="${REMOTE_URL:-https://github.com/你的用户名/beijing-dashboard.git}"
# ========================================

# 如果传入参数，覆盖默认地址
if [ -n "$1" ]; then
    REMOTE_URL="$1"
fi

echo "项目目录: $PROJECT_DIR"
echo "远程仓库: $REMOTE_URL"
echo ""

# 检查是否已有关联远程
if git remote get-url origin >/dev/null 2>&1; then
    echo "更新远程地址..."
    git remote set-url origin "$REMOTE_URL"
else
    echo "关联远程仓库..."
    git remote add origin "$REMOTE_URL"
fi

echo "推送代码到 GitHub..."
git push -u origin main

echo ""
echo "========================================"
echo "✓ 代码已推送到 GitHub"
echo ""
echo "下一步: 开启 GitHub Pages"
echo "  1. 打开浏览器访问你的仓库页面"
echo "  2. 点击 Settings (设置)"
echo "  3. 左侧菜单找到 Pages"
echo "  4. Source 选择 'Deploy from a branch'"
echo "  5. Branch 选择 main，文件夹选 /(root)"
echo "  6. 点击 Save"
echo ""
echo "等待 1-2 分钟后，你的看板将通过以下地址访问:"
echo "  https://你的用户名.github.io/beijing-dashboard/"
echo "========================================"
