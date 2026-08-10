#!/usr/bin/env bash
#
# 发布后回填 Homebrew formula 的 sha256。
#
# 用法：
#   1) 已 git tag vX.Y.Z 并 git push --tags
#   2) 运行 ./scripts/release-formula.sh
#
# 脚本会：从 pyproject.toml 读取版本 -> 对齐 Formula/ntfs-mate.rb 的 url 版本号
#         -> 下载 GitHub tag tarball -> 计算 sha256 -> 写回 formula -> git commit & push
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FORMULA="Formula/ntfs-mate.rb"
PYPROJECT="pyproject.toml"
REPO="Rock-Legend/ntfs-for-mac-cli"

# 从 pyproject.toml 读取版本号
VERSION="$(grep -oE '^version = "[0-9]+\.[0-9]+\.[0-9]+"' "$PYPROJECT" | head -1 | sed -E 's/version = "([^"]+)"/\1/')"
if [ -z "$VERSION" ]; then
  echo "错误：无法从 $PYPROJECT 读取版本号" >&2
  exit 1
fi
echo "版本：$VERSION"

# 对齐 formula 中的 url 版本号
if grep -q "archive/refs/tags/v${VERSION}.tar.gz" "$FORMULA"; then
  echo "formula url 版本已对齐 v${VERSION}"
else
  echo "更新 formula url 版本 -> v${VERSION}"
  # 仅替换同形 url 行，避免误伤其它内容
  sed -i.bak -E "s#(url \"https://github.com/${REPO}/archive/refs/tags/v)[0-9]+\.[0-9]+\.[0-9]+(\.tar\.gz\")#\1${VERSION}\2#" "$FORMULA"
  rm -f "$FORMULA.bak"
fi

TARBALL_URL="https://github.com/${REPO}/archive/refs/tags/v${VERSION}.tar.gz"
echo "下载 tarball：$TARBALL_URL"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 若本机有代理环境变量则沿用；没有则尝试探测常见代理端口
for p in "${HOMEBREW_HTTPS_PROXY:-}" "${https_proxy:-}" "http://127.0.0.1:7897" "http://127.0.0.1:7890" "http://127.0.0.1:1087"; do
  [ -z "$p" ] && continue
  if curl -fsSL -x "$p" -o "$TMP/archive.tar.gz" "$TARBALL_URL"; then
    echo "通过代理下载成功：$p"
    break
  fi
done
# 兜底：直连
if [ ! -f "$TMP/archive.tar.gz" ]; then
  curl -fsSL -o "$TMP/archive.tar.gz" "$TARBALL_URL"
fi

SHA="$(shasum -a 256 "$TMP/archive.tar.gz" | awk '{print $1}')"
echo "sha256：$SHA"

# 写回 formula（替换占位或已有 sha）
if grep -q "sha256 \"$SHA\"" "$FORMULA"; then
  echo "sha256 已是最新，无需修改"
else
  sed -i.bak -E "s/^  sha256 \"[0-9a-f]{64}\"$/  sha256 \"$SHA\"/" "$FORMULA"
  rm -f "$FORMULA.bak"
fi

echo "已更新 ${FORMULA}，提交并推送…"
git add "$FORMULA"
git commit -m "build(formula): 回填 v${VERSION} 的 sha256"
git push

echo "完成。其他用户现在可："
echo "  brew tap ${REPO}"
echo "  brew install ntfs-mate"
