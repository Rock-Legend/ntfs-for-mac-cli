# NTFS Mate — Homebrew formula
#
# 仓库地址：https://github.com/Rock-Legend/ntfs-for-mac-cli
#
# 用法（本仓库自带 Formula 目录）：
#   本地安装：  brew install --formula ./Formula/ntfs-mate.rb
#   作为 tap：  brew tap Rock-Legend/ntfs-for-mac-cli && brew install ntfs-mate
#
# 说明：
#   - macFUSE 只能走官方 cask（gromgit 没有 macfuse formula），formula 会自动拉取。
#   - ntfs-3g-mac 来自 gromgit/homebrew-fuse，brew 会自动 tap gromgit/fuse。
#   - 两者下载/编译均来自 GitHub / tuxera / ghcr.io，国内若超时请先为 brew 配置代理：
#       export HOMEBREW_HTTPS_PROXY=http://127.0.0.1:7897
#       export HOMEBREW_HTTP_PROXY=http://127.0.0.1:7897
class NtfsMate < Formula
  desc "macOS NTFS read/write TUI tool (macFUSE + ntfs-3g)"
  homepage "https://github.com/Rock-Legend/ntfs-for-mac-cli"
  url "https://github.com/Rock-Legend/ntfs-for-mac-cli/archive/refs/tags/v0.3.0.tar.gz"
  # 发布后执行 `./scripts/release-formula.sh` 自动下载 tag tarball 并回填真实 sha256。
  sha256 "0eecbe75edbc5850c20ff3cc1217116eecac99f07754888e214cd69c301a3b2c"
  license "MIT"

  depends_on "python@3.13"
  # macFUSE 系统扩展（cask）：提供 NTFS 读写所需的内核驱动框架
  depends_on "macfuse"
  # NTFS 读写驱动（来自 gromgit tap，brew 安装时自动 tap）
  depends_on "gromgit/fuse/ntfs-3g-mac"

  def install
    # 独立 venv，避免污染系统 Python；目录约定与 install.sh 保持一致。
    venv = libexec/"venv"
    python = Formula["python@3.13"].opt_bin/"python3.13"
    system python, "-m", "venv", venv
    venv_pip = venv/"bin/pip"
    system venv_pip, "install", "--upgrade", "pip"
    # 从源码构建并安装本包（pip 会从 PyPI 拉取 textual 等依赖）
    system venv_pip, "install", buildpath/"."

    (bin/"ntfs-mate").write_env_script(
      venv/"bin/ntfs-mate",
      PYTHONPATH => libexec/"lib/python3.13/site-packages",
    )
  end

  def caveats
    <<~EOS
      首次使用需要授权 macFUSE 内核扩展：
        系统设置 → 隐私与安全性 → 允许 "macFUSE"（Benjamin Fleischer），按提示重启一次（仅首次）。
        Apple Silicon 还需在恢复模式中降低安全策略一次。

      若安装 macFUSE / ntfs-3g 时遇到 GitHub 网络超时，请先为 brew 配置代理再安装：
        export HOMEBREW_HTTPS_PROXY=http://127.0.0.1:7897
        export HOMEBREW_HTTP_PROXY=http://127.0.0.1:7897
        brew install ntfs-mate

      PyPI（textual 等）若访问慢，可换国内镜像：
        pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/ntfs-mate --version")
  end
end
