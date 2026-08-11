"""mounter.py 单元测试：命令构造与错误映射（mock subprocess，不触碰真实磁盘）。"""

import pytest

from ntfs_tui.disks import NtfsVolume
from ntfs_tui.mounter import (
    MountError,
    build_mount_cmd,
    eject,
    map_error,
    mount_point_for,
    mount_ro,
    mount_rw,
    unmount,
)


def _vol(mounted=False, writable=False):
    return NtfsVolume(
        device="/dev/disk4s1",
        volume_name="MyPassport",
        size_bytes=1_000_000_000_000,
        free_bytes=500_000_000_000,
        mount_point="/Volumes/MyPassport" if mounted else "",
        writable=writable,
        whole_disk="/dev/disk4",
    )


class _Completed:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Recorder:
    """记录所有调用，可按命令前缀配置返回。"""

    def __init__(self, results=None):
        self.calls = []
        self.inputs = []
        self.results = results or {}

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        self.inputs.append(kwargs.get("input"))
        for prefix, result in self.results.items():
            if list(prefix) == list(cmd)[: len(prefix)]:
                return result
        return _Completed()


# ---------- mount_point_for ----------

def test_mount_point_for_no_conflict():
    mp = mount_point_for(_vol(), existing={"Macintosh HD"})
    assert mp == "/Volumes/MyPassport"


def test_mount_point_for_conflict_appends_device():
    mp = mount_point_for(_vol(), existing={"MyPassport"})
    assert mp == "/Volumes/MyPassport-disk4s1"


def test_mount_point_for_unnamed():
    v = _vol()
    v.volume_name = "未命名"
    mp = mount_point_for(v, existing=set())
    assert mp.startswith("/Volumes/")


# ---------- build_mount_cmd ----------

def test_build_mount_cmd_exact():
    cmd = build_mount_cmd(_vol(), "/Volumes/MyPassport")
    assert cmd == [
        "sudo", "-S", "-p", "",
        "ntfs-3g", "/dev/disk4s1", "/Volumes/MyPassport",
        "-o", "local",
        "-o", "allow_other",
        "-o", "auto_xattr",
        "-o", "auto_cache",
        "-o", "big_writes",
        "-o", "noatime",
        "-o", "volname=MyPassport",
    ]


def test_build_mount_cmd_extra_options():
    cmd = build_mount_cmd(_vol(), "/Volumes/X", extra=["remove_hiberfile"])
    assert cmd[-2:] == ["-o", "remove_hiberfile"]


# ---------- map_error ----------

def test_map_error_hibernated():
    hint = map_error("Windows is hibernated, refused to mount.")
    assert "休眠" in hint
    assert "remove_hiberfile" in hint


def test_map_error_dirty():
    hint = map_error("NTFS is marked to be dirty. Run chkdsk.")
    assert "chkdsk" in hint


def test_map_error_unclean():
    hint = map_error("The disk contains an unclean file system (0, 0).")
    assert "chkdsk" in hint


def test_map_error_other_passthrough():
    hint = map_error("some weird failure")
    assert "some weird failure" in hint


# ---------- _ensure_mount_dir（/Volumes 需 root，测试 sudo 兜底） ----------

def test_ensure_mount_dir_sudo_fallback_on_permission_error(monkeypatch):
    import ntfs_tui.mounter as m

    monkeypatch.setattr(m.os.path, "isdir", lambda p: False)

    def _denied(*a, **k):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(m.os, "makedirs", _denied)
    rec = _Recorder()
    m._ensure_mount_dir("/Volumes/Peter的备份磁盘 3", password="pw", run=rec)
    assert rec.calls == [["sudo", "-S", "-p", "", "mkdir", "-p", "/Volumes/Peter的备份磁盘 3"]]
    assert rec.inputs == [b"pw\n"]


def test_ensure_mount_dir_sudo_failure_raises(monkeypatch):
    import ntfs_tui.mounter as m

    monkeypatch.setattr(m.os.path, "isdir", lambda p: False)
    monkeypatch.setattr(m.os, "makedirs",
                        lambda *a, **k: (_ for _ in ()).throw(PermissionError()))
    rec = _Recorder(results={("sudo",): _Completed(returncode=1, stderr=b"mkdir: /Volumes: Permission denied")})
    with pytest.raises(MountError) as exc_info:
        m._ensure_mount_dir("/Volumes/X", password="pw", run=rec)
    assert "创建挂载点失败" in exc_info.value.hint


def test_ensure_mount_dir_existing_dir_noop(monkeypatch):
    import ntfs_tui.mounter as m

    monkeypatch.setattr(m.os.path, "isdir", lambda p: True)
    rec = _Recorder()
    m._ensure_mount_dir("/Volumes/X", password="pw", run=rec)
    assert rec.calls == []


# ---------- mount_rw ----------

def test_mount_rw_unmounts_first_when_mounted(monkeypatch, tmp_path):
    monkeypatch.setattr("ntfs_tui.mounter._ensure_mount_dir", lambda *a, **k: None)
    rec = _Recorder()
    mp = mount_rw(_vol(mounted=True), password="pw123", run=rec,
                  existing_volumes=set())
    assert rec.calls[0] == ["diskutil", "unmount", "/dev/disk4s1"]
    assert rec.calls[1][4] == "ntfs-3g"
    assert rec.inputs[1] == b"pw123\n"
    assert mp == "/Volumes/MyPassport"


def test_mount_rw_no_password_uses_cached_credential(monkeypatch):
    monkeypatch.setattr("ntfs_tui.mounter._ensure_mount_dir", lambda *a, **k: None)
    rec = _Recorder()
    mount_rw(_vol(mounted=False), password=None, run=rec, existing_volumes=set())
    assert rec.inputs[0] is None


def test_mount_rw_failure_raises_with_hint(monkeypatch):
    monkeypatch.setattr("ntfs_tui.mounter._ensure_mount_dir", lambda *a, **k: None)
    rec = _Recorder(results={
        ("sudo",): _Completed(returncode=1, stderr=b"Windows is hibernated, refused to mount."),
    })
    with pytest.raises(MountError) as exc_info:
        mount_rw(_vol(), password="pw", run=rec, existing_volumes=set())
    assert "休眠" in exc_info.value.hint


# ---------- mount_ro / unmount / eject ----------

def test_mount_ro_command():
    rec = _Recorder()
    mount_ro(_vol(), run=rec)
    assert rec.calls == [["diskutil", "mount", "readOnly", "/dev/disk4s1"]]


def test_unmount_command():
    rec = _Recorder()
    unmount(_vol(mounted=True), run=rec)
    assert rec.calls == [["diskutil", "unmount", "/dev/disk4s1"]]


def test_eject_uses_whole_disk():
    rec = _Recorder()
    eject(_vol(), run=rec)
    assert rec.calls == [["diskutil", "eject", "/dev/disk4"]]
