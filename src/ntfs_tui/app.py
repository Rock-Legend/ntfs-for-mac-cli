"""NTFS Mate — Textual TUI 主界面。"""

from __future__ import annotations

import importlib.metadata
import shutil
import sys
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Grid, Horizontal, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Input, Label, Static

from .deps import check_deps
from .disks import NtfsVolume, list_ntfs_volumes
from .mounter import (
    MountError,
    eject,
    mount_ro,
    mount_rw,
    open_in_finder,
    unmount,
)


class PasswordScreen(ModalScreen[str | None]):
    """sudo 密码输入弹窗。返回密码字符串；取消返回 None。"""

    BINDINGS = [Binding("escape", "cancel", "取消")]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog", classes="password"):
            yield Label("需要管理员权限", id="dialog-title")
            yield Label(
                "挂载为读写需要 sudo 授权。密码仅用于本次命令，不会被保存。",
                id="dialog-subtitle",
            )
            yield Input(
                password=True,
                placeholder="输入开机密码…",
                id="pw",
            )
            with Horizontal(id="dialog-buttons"):
                yield Button("确定", id="ok", variant="primary")
                yield Button("取消", id="cancel", variant="default")

    def on_mount(self) -> None:
        self.query_one("#pw", Input).focus()

    @on(Input.Submitted, "#pw")
    @on(Button.Pressed, "#ok")
    def confirm(self) -> None:
        self.dismiss(self.query_one("#pw", Input).value)

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)


class MessageScreen(ModalScreen[None]):
    """信息/错误展示弹窗。"""

    BINDINGS = [
        Binding("escape", "close", "关闭"),
        Binding("enter", "close", "关闭"),
    ]

    ICONS = {
        "info": "◈",
        "success": "✓",
        "warning": "▲",
        "error": "✕",
    }

    def __init__(self, title: str, message: str, *, severity: str = "info"):
        super().__init__()
        self._title = title
        self._message = message
        self._severity = severity if severity in self.ICONS else "info"

    def compose(self) -> ComposeResult:
        kind = self._severity
        with Vertical(id="dialog", classes=kind):
            yield Label(self._title, id="dialog-title")
            yield Label(self._message, id="dialog-message")
            with Horizontal(id="dialog-buttons"):
                yield Button("知道了", id="ok", variant="primary")

    @on(Button.Pressed, "#ok")
    def action_close(self) -> None:
        self.dismiss(None)


class NTFSApp(App):
    """NTFS Mate 主应用。"""

    TITLE = "NTFS Mate"
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    /* ---------- 全局调色盘 ---------- */
    $gradient-start: #00d4ff;
    $gradient-end: #7b2ff7;
    $neon-cyan: #00f0ff;
    $neon-purple: #bf5af2;
    $neon-red: #ff453a;
    $neon-green: #30d158;
    $neon-yellow: #ffd60a;
    $surface-dark: #0f172a;
    $surface-panel: #1e293b;
    $surface-light: #334155;

    Screen { background: $surface-dark; }

    /* ---------- 顶栏 ---------- */
    #topbar {
        height: 3;
        padding: 1 2;
        background: $surface-panel;
        color: $text;
        border-bottom: hkey $neon-cyan;
        text-style: bold;
    }
    #topbar Static { color: $text; }
    #dep-badge { color: $text-muted; }

    /* ---------- 表格区 ---------- */
    #table-box {
        height: 1fr;
        background: $surface-dark;
        margin: 0 2;
    }
    DataTable {
        height: 1fr;
        background: $surface-dark;
        border-top: hkey $surface-light;
        border-bottom: hkey $surface-light;
    }
    DataTable > .datatable--header {
        background: $surface-dark;
        background-tint: transparent 0%;
        color: $neon-cyan;
        text-style: bold;
    }
    DataTable:focus > .datatable--header {
        background-tint: transparent 0%;
    }
    DataTable > .datatable--header-hover {
        background: $surface-dark;
        background-tint: transparent 0%;
    }
    DataTable > .datatable--cursor {
        background: $surface-light;
    }
    DataTable > .datatable--hover {
        background: $surface-panel;
    }

    /* ---------- 详情面板 ---------- */
    #detail {
        height: auto;
        max-height: 7;
        padding: 1 2;
        margin: 0 2 1 2;
        border: solid $surface-light;
        background: $surface-panel;
        color: $text;
    }

    /* ---------- 弹框通用 ---------- */
    #dialog {
        width: 40;
        height: auto;
        padding: 1 2;
        background: $surface-panel;
        border: solid $neon-cyan;
        box-sizing: border-box;
        align: center middle;
    }
    #dialog-title {
        width: 100%;
        height: auto;
        padding: 0 0 1 0;
        text-style: bold;
        color: $text;
        content-align: center middle;
    }
    #dialog-subtitle,
    #dialog-message {
        width: 100%;
        padding: 0 0 1 0;
        color: $text-muted;
        text-align: center;
    }
    #dialog-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0 0 0;
    }
    #dialog-buttons Button {
        min-width: 10;
        height: 3;
        margin: 0 1;
        border: solid $surface-light;
        background: $surface-light;
        color: $text;
        content-align: center middle;
    }
    #dialog-buttons Button:first-child { margin-left: 0; }
    #dialog-buttons Button:last-child { margin-right: 0; }
    #dialog-buttons Button:focus {
        border: tall $neon-cyan;
        background: $surface-panel;
    }

    /* 密码弹框 */
    #dialog.password { border: solid $neon-purple; }
    #dialog.password #dialog-title { color: $neon-purple; }
    #dialog.password Input {
        height: 3;
        margin: 0 0 1 0;
        padding: 0 1;
        border: solid $surface-light;
        background: $surface-dark;
    }
    #dialog.password Input:focus { border: tall $neon-purple; }

    /* 错误弹框 */
    #dialog.error { border: solid $neon-red; }
    #dialog.error #dialog-title { color: $neon-red; }

    /* 成功弹框 */
    #dialog.success { border: solid $neon-green; }
    #dialog.success #dialog-title { color: $neon-green; }

    /* 警告弹框 */
    #dialog.warning { border: solid $neon-yellow; }
    #dialog.warning #dialog-title { color: $neon-yellow; }

    /* ---------- 按钮变体 ---------- */
    Button { border: solid $surface-light; background: $surface-light; color: $text; }
    Button:hover { background: $surface-panel; }
    Button:focus { border: tall $neon-cyan; }
    Button.-primary { background: $neon-cyan; color: $surface-dark; border: none; }
    Button.-primary:hover { background: #5ce1ff; }
    Button.-error { background: $neon-red; color: $text; border: none; }
    Button.-error:hover { background: #ff6b5f; }

    /* ---------- 通知 ---------- */
    .textual-notification {
        border-left: outer $neon-cyan;
        background: $surface-panel;
        color: $text;
        padding: 1 2;
    }
    .textual-notification.-information { border-left: outer $neon-cyan; }
    .textual-notification.-success { border-left: outer $neon-green; }
    .textual-notification.-warning { border-left: outer $neon-yellow; }
    .textual-notification.-error { border-left: outer $neon-red; }

    /* ---------- 页脚 ---------- */
    Footer {
        background: $surface-panel;
        color: $text;
    }
    FooterKey {
        color: $neon-cyan;
        text-style: bold;
        background: $surface-panel;
    }
    FooterLabel {
        color: $text-muted;
        background: $surface-panel;
    }
    """

    BINDINGS = [
        Binding("m", "mount_rw", "挂载读写"),
        Binding("r", "mount_ro", "只读挂载"),
        Binding("u", "unmount", "卸载"),
        Binding("e", "eject", "弹出"),
        Binding("o", "open_finder", "访达打开"),
        Binding("d", "deps", "依赖安装"),
        Binding("f5", "refresh", "刷新"),
        Binding("q", "quit", "退出"),
    ]

    def __init__(self):
        super().__init__()
        self.volumes: list[NtfsVolume] = []

    def compose(self) -> ComposeResult:
        yield Static(id="topbar")
        with Vertical(id="table-box"):
            yield DataTable(cursor_type="row")
        yield Static("暂无 NTFS 磁盘", id="detail")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("卷名", "设备", "总容量", "可用", "状态", "挂载点")
        self._update_dep_badge()
        self.refresh_disks()
        self.set_interval(3, self.refresh_disks)

    # ---------- 界面更新 ----------

    def _update_dep_badge(self) -> None:
        st = check_deps()
        def mark(ok: bool) -> str:
            return "✓" if ok else "✗"
        badge = f"macFUSE {mark(st.macfuse)}  ntfs-3g {mark(st.ntfs3g)}  brew {mark(st.brew)}"
        self.query_one("#topbar", Static).update(
            f"NTFS Mate — macOS NTFS 读写工具    [dep]{badge}[/dep]"
        )

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        cursor = table.cursor_row
        table.clear()
        for i, v in enumerate(self.volumes):
            style = {"未挂载": "yellow", "只读": "cyan", "读写": "green"}[v.status]
            table.add_row(
                v.volume_name, v.device, v.size_gb, v.free_gb,
                f"[{style}]{v.status}[/{style}]",
                v.mount_point or "-",
                key=str(i),
            )
        if self.volumes and cursor < len(self.volumes):
            table.move_cursor(row=cursor)
        self._render_detail(self.selected_volume())

    def _render_detail(self, v: NtfsVolume | None) -> None:
        detail = self.query_one("#detail", Static)
        if v is None:
            detail.update("未检测到 NTFS 磁盘 — 插入磁盘后会自动出现（每 3 秒刷新）")
            return
        detail.update(
            f"卷名：{v.volume_name}   设备：{v.device}   所属磁盘：{v.whole_disk}\n"
            f"容量：{v.size_gb}（可用 {v.free_gb}）   状态：{v.status}   "
            f"挂载点：{v.mount_point or '-'}"
        )

    def selected_volume(self) -> NtfsVolume | None:
        if not self.volumes:
            return None
        row = self.query_one(DataTable).cursor_row
        if row is None or row >= len(self.volumes):
            return self.volumes[0]
        return self.volumes[row]

    @on(DataTable.RowHighlighted)
    def _on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is not None:
            idx = int(event.row_key.value)
            if idx < len(self.volumes):
                self._render_detail(self.volumes[idx])

    # ---------- 数据刷新 ----------

    @work(thread=True)
    def refresh_disks(self) -> None:
        try:
            vols = list_ntfs_volumes()
        except Exception as e:
            self.call_from_thread(
                self.notify, f"磁盘探测失败：{e}", severity="error"
            )
            return
        self.call_from_thread(self._apply_volumes, vols)

    def _apply_volumes(self, vols: list[NtfsVolume]) -> None:
        self.volumes = vols
        self._render_table()

    def action_refresh(self) -> None:
        self.refresh_disks()

    # ---------- 操作 ----------

    def action_mount_rw(self) -> None:
        v = self.selected_volume()
        if v is None:
            self.notify("⚠️ 未检测到 NTFS 磁盘", severity="warning")
            return
        if v.mount_point and v.writable:
            self.notify(f"✅ {v.volume_name} 已是读写挂载", severity="information")
            return
        self.push_screen(PasswordScreen(), lambda pw: self._start_mount_rw(v, pw))

    def _start_mount_rw(self, v: NtfsVolume, password: str | None) -> None:
        if not password:
            return  # 用户取消
        self._do_mount_rw(v, password)

    @work(thread=True)
    def _do_mount_rw(self, v: NtfsVolume, password: str) -> None:
        try:
            mp = mount_rw(v, password)
        except MountError as e:
            self.call_from_thread(
                self.push_screen, MessageScreen("挂载失败", e.hint, severity="error")
            )
        except Exception as e:  # 兜底：任何异常都不应让 TUI 崩溃
            self.call_from_thread(
                self.push_screen,
                MessageScreen("挂载失败", f"未预期的错误：{type(e).__name__}: {e}", error=True),
            )
        else:
            self.call_from_thread(self.notify, f"✅ 已读写挂载到 {mp}", severity="success")
        finally:
            self.call_from_thread(self.refresh_disks)

    @work(thread=True)
    def _run_simple(self, fn, v: NtfsVolume, ok_msg: str, fail_title: str) -> None:
        try:
            fn(v)
        except MountError as e:
            self.call_from_thread(
                self.push_screen, MessageScreen(fail_title, e.hint, severity="error")
            )
        except Exception as e:  # 兜底：任何异常都不应让 TUI 崩溃
            self.call_from_thread(
                self.push_screen,
                MessageScreen(fail_title, f"未预期的错误：{type(e).__name__}: {e}", severity="error"),
            )
        else:
            self.call_from_thread(self.notify, ok_msg.format(v=v), severity="success")
        finally:
            self.call_from_thread(self.refresh_disks)

    def action_mount_ro(self) -> None:
        v = self.selected_volume()
        if v is None:
            self.notify("⚠️ 未检测到 NTFS 磁盘", severity="warning")
            return
        if v.mount_point:
            self.notify(f"ℹ {v.volume_name} 已挂载（{v.status}）", severity="information")
            return
        self._run_simple(mount_ro, v, "✅ {v.volume_name} 已只读挂载", "只读挂载失败")

    def action_unmount(self) -> None:
        v = self.selected_volume()
        if v is None or not v.mount_point:
            self.notify("⚠️ 该磁盘未挂载", severity="warning")
            return
        self._run_simple(unmount, v, "✅ {v.volume_name} 已卸载", "卸载失败")

    def action_eject(self) -> None:
        v = self.selected_volume()
        if v is None:
            self.notify("⚠️ 未检测到 NTFS 磁盘", severity="warning")
            return
        self._run_simple(eject, v, "✅ {v.whole_disk} 已弹出，可安全拔出", "弹出失败")

    def action_open_finder(self) -> None:
        v = self.selected_volume()
        if v is None or not v.mount_point:
            self.notify("⚠️ 该磁盘未挂载，无法打开", severity="warning")
            return
        open_in_finder(v)

    def action_deps(self) -> None:
        st = check_deps()
        if st.all_ok:
            self.push_screen(MessageScreen("依赖状态", "macFUSE、ntfs-3g、brew 均已就绪", severity="success"))
        else:
            self.push_screen(MessageScreen(
                "缺少依赖",
                "请在终端执行：\n\n"
                "  brew install --cask macfuse\n"
                "  brew tap gromgit/homebrew-fuse\n"
                "  brew install gromgit/fuse/ntfs-3g-mac\n\n"
                "或重新运行源码包中的 install.sh。\n"
                "首次使用还需在 系统设置 → 隐私与安全性 允许 macFUSE。",
                severity="warning",
            ))


def get_version() -> str:
    """版本号单一数据源是 pyproject.toml；源码直接运行时退回 dev 标识。"""
    try:
        return importlib.metadata.version("ntfs-mate")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0-dev（源码运行，未安装）"


USAGE = """ntfs-mate — macOS NTFS 硬盘读写 TUI 工具

用法:
  ntfs-mate                 启动 TUI
  ntfs-mate -v, --version   显示版本与驱动状态
  ntfs-mate -h, --help      显示本帮助
  ntfs-mate uninstall       卸载本工具（移除全局命令与应用本体，保留驱动）；Homebrew 安装请用 `brew uninstall ntfs-mate`
"""


def _install_prefix() -> Path | None:
    """定位系统安装根目录（含 ntfs-mate 的那一级 keg / 安装目录）。

    支持两种布局：
      - 手动/系统安装：<prefix>/ntfs-mate/venv/bin/python
      - Homebrew：    <Cellar>/ntfs-mate/<version>/libexec/venv/bin/python
    源码/开发环境运行（都不匹配）时返回 None。

    注意：不得使用 Path(sys.executable).resolve()。venv 内的 python 是软链，
    指向 base interpreter（如 /usr/local/Cellar/python@3.13/...），resolve 会
    破坏 "…/venv" 布局假设；直接用 sys.executable 的目录向上回溯即可。
    """
    venv = Path(sys.executable).parent.parent  # .../venv（不 resolve，保留软链目录）
    if venv.name != "venv":
        return None
    # 手动安装：venv 直接挂在 ntfs-mate 下
    if venv.parent.name == "ntfs-mate":
        return venv.parent
    # Homebrew：venv 在 libexec 下，再往上是 <version>/ntfs-mate
    if venv.parent.name == "libexec":
        gp = venv.parent.parent.parent  # 跳过 <version> 目录，应为 ntfs-mate
        if gp.name == "ntfs-mate":
            return venv.parent.parent  # 返回 versioned keg 目录
    return None


def _is_brew_install(prefix: Path) -> bool:
    """是否由 Homebrew 管理（路径落在 Cellar 内，或 opt 下为软链）。"""
    resolved = prefix.resolve()
    if "Cellar" in resolved.parts:
        return True
    return prefix.parent.name == "opt" and prefix.is_symlink()


def self_uninstall(app_dir: Path, bin_link: Path, confirm=input) -> bool:
    """移除全局命令与应用本体。confirm 返回非 y 则取消。返回是否执行了卸载。"""
    answer = confirm(
        f"将删除 {app_dir} 与 {bin_link}（macFUSE/ntfs-3g 驱动保留）。确认卸载？[y/N] "
    )
    if answer.strip().lower() != "y":
        print("已取消。")
        return False
    bin_link.unlink(missing_ok=True)
    shutil.rmtree(app_dir, ignore_errors=True)
    print("✅ 已卸载 ntfs-mate。")
    return True


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if not arg:
        NTFSApp().run()
        return
    if arg in ("-v", "--version", "version"):
        st = check_deps()
        print(f"ntfs-mate {get_version()}")
        print(f"  macFUSE: {'✓' if st.macfuse else '✗ 未安装'}   "
              f"ntfs-3g: {'✓' if st.ntfs3g else '✗ 未安装'}   "
              f"brew: {'✓' if st.brew else '✗ 未安装'}")
        return
    if arg in ("-h", "--help", "help"):
        print(USAGE)
        return
    if arg == "uninstall":
        prefix = _install_prefix()
        if prefix is None:
            print("当前为源码/开发环境运行，未检测到系统安装，无需卸载。", file=sys.stderr)
            sys.exit(1)
        if _is_brew_install(prefix):
            print("检测到通过 Homebrew 安装，请勿用本命令卸载，请改用：", file=sys.stderr)
            print("    brew uninstall ntfs-mate", file=sys.stderr)
            sys.exit(1)
        bin_link = prefix.parent.parent / "bin" / "ntfs-mate"
        self_uninstall(prefix, bin_link)
        return
    print(f"ntfs-mate: 未知参数 '{arg}'\n", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
