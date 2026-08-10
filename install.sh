#!/bin/bash
# NTFS Mate 一键安装脚本
#
# 标准 CLI 安装（遵循 Homebrew 目录惯例）：
#   应用本体  → $(brew --prefix)/opt/ntfs-mate/   （独立 venv，与源码目录无关）
#   全局命令  → $(brew --prefix)/bin/ntfs-mate
# 安装完成后，本源码目录可以删除。
#
# 网络稳健性（国内必看）：
#   macFUSE(cask) 与 ntfs-3g-mac 的下载/编译都来自 GitHub / tuxera / ghcr.io，
#   直连极易超时（curl 28）。本脚本会自动探测本机代理并让 brew/git/curl 全部走代理；
#   若未探测到代理，会给出手动配置提示。所有 brew 操作均带重试退避。
set -euo pipefail

cd "$(dirname "$0")"

info()  { printf '\033[1;34m[安装]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[提示]\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[错误]\033[0m %s\n' "$*"; exit 1; }

# ---------- 0. 检查 Homebrew ----------
if ! command -v brew >/dev/null 2>&1; then
    error "未找到 Homebrew。请先安装：
  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"
安装完成后重新运行本脚本。"
fi
export HOMEBREW_NO_AUTO_UPDATE=1
BREW_PREFIX="$(brew --prefix)"          # Intel: /usr/local, Apple Silicon: /opt/homebrew
APP_DIR="$BREW_PREFIX/opt/ntfs-mate"
BIN_DIR="$BREW_PREFIX/bin"
info "Homebrew ✓ (prefix: $BREW_PREFIX)"

# ---------- 1. 代理自适应（核心：让 brew / git / curl 真正走代理）----------
# 关键坑：brew 默认不读 https_proxy，只认 HOMEBREW_HTTPS_PROXY；
# git clone tap 走 https_proxy 也需显式；所以三套变量一起设。
# 若终端未配置代理，自动探测本机常见代理端口（Clash/Surge/Shadowrocket 等）并仅为本次安装启用。
setup_proxy() {
    if [ -n "${HOMEBREW_HTTPS_PROXY:-}${https_proxy:-}${HTTPS_PROXY:-}" ]; then
        info "检测到代理环境变量，brew/git/curl 将走代理。"
        return 0
    fi
    local port="" found=""
    for port in 7897 7890 1087 8889 1080 10808 7891 8118 10809; do
        if nc -z -w 1 127.0.0.1 "$port" 2>/dev/null; then
            # 验证该端口确实能代理出网（避免误判未启动代理的端口）
            if curl -x "http://127.0.0.1:$port" -m 8 -sfI https://github.com >/dev/null 2>&1; then
                found="http://127.0.0.1:$port"
                break
            fi
        fi
    done
    if [ -n "$found" ]; then
        export http_proxy="$found" https_proxy="$found" \
               HTTP_PROXY="$found" HTTPS_PROXY="$found" \
               all_proxy="$found" ALL_PROXY="$found" \
               HOMEBREW_HTTP_PROXY="$found" HOMEBREW_HTTPS_PROXY="$found"
        info "检测到本机代理 ${found}，已为本次安装启用（brew/git/curl 均生效）。"
    else
        warn "未检测到代理，将直连 GitHub 安装 macFUSE / ntfs-3g（国内很可能超时）。
  若失败，请先手动配置代理后重跑本脚本：
    export HOMEBREW_HTTPS_PROXY=http://127.0.0.1:7897
    export HOMEBREW_HTTP_PROXY=http://127.0.0.1:7897
    ./install.sh"
    fi
}
setup_proxy

# ---------- 2. 重试辅助 ----------
# retry <描述> <命令...>：失败按 1/2/3 秒退避重试，最多 4 次。
retry() {
    local desc="$1"; shift
    local attempt rc
    for attempt in 1 2 3 4; do
        if "$@"; then return 0; fi
        rc=$?
        if [ "$attempt" -lt 4 ]; then
            warn "${desc} 第 ${attempt} 次失败 (rc=${rc})，${attempt} 秒后重试..."
            sleep "$attempt"
        else
            warn "${desc} 多次失败。"
            return "$rc"
        fi
    done
}

# ---------- 3. 非交互 brew install（保真退出码）----------
# 有限个 y 覆盖依赖升级的 [y/N] 确认（不用 yes：无限输出且被 SIGPIPE 杀导致误判），
# 并过滤回显的 y 行，保留真实退出码。
brew_install() {
    local log rc
    log="$(printf 'y\n%.0s' {1..40} | brew install "$@" 2>&1)"
    rc=$?
    printf '%s\n' "$log" | grep -vE '^[yY]$' || true
    return "$rc"
}

# ---------- 4. 安装 macFUSE ----------
# 注意：macFUSE 只能走官方 cask（gromgit 没有 macfuse formula）。
# cask 会运行 pkg 安装器装全（含 /usr/local/include/fuse.h）；"只装一半"是之前安装
# 中断或未批准内核扩展导致。以 fuse.h 是否存在作为安装完整性的硬校验。
install_macfuse() {
    if [ -f /usr/local/include/fuse.h ]; then
        info "macFUSE 已安装 ✓"
        return 0
    fi
    info "安装 macFUSE（cask，会运行 pkg 安装器；可能需开机密码与内核扩展批准）..."
    retry "安装 macFUSE" brew install --cask macfuse || true
    if [ -f /usr/local/include/fuse.h ]; then
        info "macFUSE 已安装 ✓"
        return 0
    fi
    # 兜底：cask 下载了 pkg 但未完成安装（极少数情况）
    PKG="$(ls -d "$BREW_PREFIX"/Caskroom/macfuse/*/"Install macFUSE.pkg" 2>/dev/null | head -1 || true)"
    if [ -n "$PKG" ]; then
        open "$PKG"
        error "macFUSE 的 pkg 已下载但未完成安装，已为你打开安装器。
  按提示完成（需开机密码，并在 系统设置 → 隐私与安全性 允许 macFUSE 内核扩展），然后重跑本脚本。"
    else
        error "macFUSE 安装失败。请手动执行：brew install --cask macfuse
  若提示网络超时，请先按上方提示配置代理后重试。"
    fi
}
install_macfuse

# ---------- 5. 安装 ntfs-3g-mac ----------
# 来自 gromgit/homebrew-fuse，源码编译（tuxera.com 下载）或 ghcr.io bottle，均需联网。
install_ntfs3g() {
    if brew list ntfs-3g-mac >/dev/null 2>&1; then
        info "ntfs-3g-mac 已安装 ✓"
        return 0
    fi
    info "安装 ntfs-3g-mac（gromgit/homebrew-fuse，源码编译需几分钟）..."
    retry "brew tap gromgit/fuse" brew tap gromgit/fuse || true
    if retry "安装 ntfs-3g-mac" brew_install gromgit/fuse/ntfs-3g-mac; then
        info "ntfs-3g-mac 已安装 ✓"
        return 0
    fi
    error "ntfs-3g-mac 安装失败。常见原因与处理：
  1) GitHub 网络超时 —— 先配置代理（见上方提示）后重跑；
  2) 已存在旧版但 brew 未识别 —— 先执行：brew uninstall ntfs-3g-mac，再重跑本脚本。"
}
install_ntfs3g

# ---------- 6. 打包安装到系统标准位置 ----------
# 旧版先备份，构建失败自动回滚；venv 必须在最终路径原地构建，shebang 不可迁移。
PYTHON="$(command -v python3 || true)"
[ -n "$PYTHON" ] || error "未找到 python3，请安装 Xcode 命令行工具：xcode-select --install"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
    || error "需要 Python 3.9+（当前：$("$PYTHON" -V 2>&1)）"

[ -w "$BREW_PREFIX/opt" ] || error "$BREW_PREFIX/opt 不可写，请检查 Homebrew 安装权限"

PREV_DIR="$BREW_PREFIX/opt/.ntfs-mate.previous"
rm -rf "$PREV_DIR"
if [ -d "$APP_DIR" ]; then
    OLD_VER="$("$APP_DIR/venv/bin/python" -c 'import importlib.metadata as m; print(m.version("ntfs-mate"))' 2>/dev/null || echo 未知)"
    info "检测到已安装版本 ${OLD_VER}，正在升级（旧版已备份）..."
    mv "$APP_DIR" "$PREV_DIR"
fi

info "构建并安装应用本体..."
if ! (
    "$PYTHON" -m venv "$APP_DIR/venv" &&
    "$APP_DIR/venv/bin/pip" install --quiet --upgrade pip &&
    "$APP_DIR/venv/bin/pip" install --quiet .
); then
    rm -rf "$APP_DIR"
    [ -d "$PREV_DIR" ] && mv "$PREV_DIR" "$APP_DIR" && warn "构建失败，已回滚到旧版本。"
    exit 1
fi
rm -rf "$PREV_DIR"
info "应用本体：$APP_DIR"

# ---------- 7. 注册全局命令 ----------
ln -sf "$APP_DIR/venv/bin/ntfs-mate" "$BIN_DIR/ntfs-mate"
info "全局命令已注册：$BIN_DIR/ntfs-mate"

NEW_VER="$("$APP_DIR/venv/bin/python" -c 'import importlib.metadata as m; print(m.version("ntfs-mate"))')"

cat <<EOF

✅ 安装完成！ntfs-mate $NEW_VER

⚠️  首次使用 macFUSE 需要授权内核扩展：
    系统设置 → 隐私与安全性 → 允许 "macFUSE"（Benjamin Fleischer），
    按提示重启一次电脑（仅首次需要）。
    Apple Silicon 还需在恢复模式中降低安全策略一次。

🚀 使用（终端任意目录）：
    ntfs-mate

📦 安装位置：${APP_DIR}（与源码目录无关，本目录现在可以删除）
🗑  卸载：ntfs-mate uninstall
EOF
