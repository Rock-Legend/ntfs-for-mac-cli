"""挂载管理：ntfs-3g 读写挂载、只读挂载、卸载、弹出、访达打开。"""

from __future__ import annotations

import os
import subprocess

from .disks import NtfsVolume


class MountError(Exception):
    """挂载相关操作失败。hint 为给用户的中文可操作建议。"""

    def __init__(self, stderr: str, hint: str):
        super().__init__(hint)
        self.stderr = stderr
        self.hint = hint


def mount_point_for(v: NtfsVolume, existing: set | None = None) -> str:
    """生成挂载点：/Volumes/<卷名>，重名时追加设备号。"""
    if existing is None:
        try:
            existing = set(os.listdir("/Volumes"))
        except OSError:
            existing = set()
    base = v.volume_name or "未命名"
    name = base
    if name in existing:
        name = f"{base}-{os.path.basename(v.device)}"
    return f"/Volumes/{name}"


def build_mount_cmd(v: NtfsVolume, mp: str, extra: list[str] | None = None) -> list[str]:
    cmd = [
        "sudo", "-S", "-p", "",
        "ntfs-3g", v.device, mp,
        "-o", "local",
        "-o", "allow_other",
        "-o", "auto_xattr",
        "-o", "auto_cache",
        "-o", f"volname={v.volume_name}",
    ]
    for opt in extra or []:
        cmd += ["-o", opt]
    return cmd


def map_error(stderr: str) -> str:
    """把 ntfs-3g/diskutil 的英文错误映射为中文可操作建议。"""
    low = stderr.lower()
    if "hibernat" in low:
        return (
            "检测到 Windows 休眠文件，NTFS 拒绝挂载。\n"
            "建议：在 Windows 中彻底关机（关闭「快速启动」）后重试；\n"
            "或允许工具移除休眠文件后重试（自动加 -o remove_hiberfile）。"
        )
    if "dirty" in low or "unclean" in low or "did not shut down" in low:
        return (
            "NTFS 日志未正常关闭（上次未安全弹出）。\n"
            "建议在 Windows 中运行 chkdsk /f 修复后重试。"
        )
    if "try again" in low or "incorrect password" in low:
        return "开机密码输入错误，请重试。"
    if "invalid argument" in low and "macfuse" in low:
        return "macFUSE 内核扩展未加载，请先在 系统设置 → 隐私与安全性 中允许 macFUSE。"
    return stderr.strip() or "未知错误"


def _ensure_mount_dir(mp: str, password: str | None = None, run=subprocess.run) -> None:
    """创建挂载点。/Volumes 属 root:wheel，普通用户创建会 PermissionError，需 sudo 补建。"""
    if os.path.isdir(mp):
        return
    try:
        os.makedirs(mp, exist_ok=True)
        return
    except PermissionError:
        pass
    kwargs: dict = {"capture_output": True}
    if password is not None:
        kwargs["input"] = (password + "\n").encode()
    result = run(["sudo", "-S", "-p", "", "mkdir", "-p", mp], **kwargs)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace") if isinstance(result.stderr, bytes) else str(result.stderr)
        raise MountError(stderr, "创建挂载点失败：" + map_error(stderr))


def _check(result, action: str) -> None:
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace") if isinstance(result.stderr, bytes) else str(result.stderr)
        raise MountError(stderr, f"{action}失败：{map_error(stderr)}")


def mount_rw(
    v: NtfsVolume,
    password: str | None,
    run=subprocess.run,
    existing_volumes: set | None = None,
    extra: list[str] | None = None,
) -> str:
    """读写挂载。已挂载（系统只读）时先卸载。返回挂载点。

    password 经 sudo -S 的 stdin 传入；为 None 时依赖缓存的 sudo 凭证。
    """
    if v.mount_point:
        _check(run(["diskutil", "unmount", v.device], capture_output=True), "卸载只读挂载")

    mp = mount_point_for(v, existing_volumes)
    _ensure_mount_dir(mp, password, run)

    cmd = build_mount_cmd(v, mp, extra=extra)
    kwargs: dict = {"capture_output": True}
    if password is not None:
        kwargs["input"] = (password + "\n").encode()
    result = run(cmd, **kwargs)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace") if isinstance(result.stderr, bytes) else str(result.stderr)
        raise MountError(stderr, map_error(stderr))
    return mp


def mount_ro(v: NtfsVolume, run=subprocess.run) -> str:
    """只读挂载（macOS 原生驱动）。"""
    _check(run(["diskutil", "mount", "readOnly", v.device], capture_output=True), "只读挂载")
    return f"/Volumes/{v.volume_name}"


def unmount(v: NtfsVolume, run=subprocess.run) -> None:
    """卸载卷。"""
    _check(run(["diskutil", "unmount", v.device], capture_output=True), "卸载")


def eject(v: NtfsVolume, run=subprocess.run) -> None:
    """弹出整盘（可安全拔出）。"""
    _check(run(["diskutil", "eject", v.whole_disk], capture_output=True), "弹出")


def open_in_finder(v: NtfsVolume, run=subprocess.run) -> None:
    """在访达中打开挂载点。"""
    if v.mount_point:
        run(["open", v.mount_point], capture_output=True)
