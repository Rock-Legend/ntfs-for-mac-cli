"""disks.py 单元测试：diskutil plist 解析（内置 fixture，不触碰真实磁盘）。"""

import plistlib

from ntfs_tui.disks import (
    NtfsVolume,
    is_ntfs_info,
    list_ntfs_volumes,
    volume_from_info,
)

# ---------- fixtures ----------

NTFS_INFO_RO = {
    "DeviceNode": "/dev/disk4s1",
    "DeviceIdentifier": "disk4s1",
    "VolumeName": "MyPassport",
    "FilesystemName": "NTFS",
    "Content": "Windows_NTFS",
    "TotalSize": 1_000_204_886_016,
    "FreeSpace": 322_122_547_200,
    "MountPoint": "/Volumes/MyPassport",
    "WritableVolume": False,
    "ParentWholeDisk": "/dev/disk4",
}

NTFS_INFO_UNMOUNTED = {
    "DeviceNode": "/dev/disk5s1",
    "DeviceIdentifier": "disk5s1",
    "VolumeName": "",
    "FilesystemName": "NTFS",
    "Content": "Windows_NTFS",
    "TotalSize": 500_107_862_016,
    "FreeSpace": 0,
    "MountPoint": "",
    "WritableVolume": False,
    "ParentWholeDisk": "/dev/disk5",
}

# 经 ntfs-3g 挂载后：Content 仍是 Windows_NTFS，但 FilesystemName 变为 fusefs
NTFS_INFO_FUSE_RW = {
    "DeviceNode": "/dev/disk4s1",
    "DeviceIdentifier": "disk4s1",
    "VolumeName": "MyPassport",
    "FilesystemName": "fusefs",
    "Content": "Windows_NTFS",
    "TotalSize": 1_000_204_886_016,
    "FreeSpace": 322_122_547_200,
    "MountPoint": "/Volumes/MyPassport",
    "WritableVolume": True,
    "ParentWholeDisk": "/dev/disk4",
}

APFS_INFO = {
    "DeviceNode": "/dev/disk1s1",
    "DeviceIdentifier": "disk1s1",
    "VolumeName": "Macintosh HD",
    "FilesystemName": "APFS",
    "Content": "Apple_APFS",
    "TotalSize": 500_000_000_000,
    "MountPoint": "/System/Volumes/Data",
    "WritableVolume": True,
    "ParentWholeDisk": "/dev/disk1",
}

EXFAT_INFO = {
    "DeviceNode": "/dev/disk6s1",
    "DeviceIdentifier": "disk6s1",
    "VolumeName": "UDISK",
    "FilesystemName": "ExFAT",
    "Content": "Microsoft Basic Data",
    "TotalSize": 32_000_000_000,
    "MountPoint": "/Volumes/UDISK",
    "WritableVolume": True,
    "ParentWholeDisk": "/dev/disk6",
}

LIST_PLIST = {
    "AllDisksAndPartitions": [
        {"DeviceIdentifier": "disk1", "Partitions": [{"DeviceIdentifier": "disk1s1"}]},
        {"DeviceIdentifier": "disk4", "Partitions": [{"DeviceIdentifier": "disk4s1"}]},
        {"DeviceIdentifier": "disk6", "Partitions": [{"DeviceIdentifier": "disk6s1"}]},
    ]
}

INFO_BY_ID = {
    "disk1s1": APFS_INFO,
    "disk4s1": NTFS_INFO_RO,
    "disk6s1": EXFAT_INFO,
}


class _Completed:
    def __init__(self, payload: dict):
        self.returncode = 0
        self.stdout = plistlib.dumps(payload)
        self.stderr = b""


def _fake_run_factory(info_by_id, listing=None):
    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["diskutil", "list", "-plist"]:
            return _Completed(listing if listing is not None else LIST_PLIST)
        if cmd[:3] == ["diskutil", "info", "-plist"]:
            return _Completed(info_by_id[cmd[3]])
        raise AssertionError(f"unexpected command: {cmd}")

    return fake_run


# ---------- is_ntfs_info ----------

def test_is_ntfs_info_true():
    assert is_ntfs_info(NTFS_INFO_RO) is True
    assert is_ntfs_info(NTFS_INFO_FUSE_RW) is True  # Content 仍是 Windows_NTFS


def test_is_ntfs_info_false():
    assert is_ntfs_info(APFS_INFO) is False
    assert is_ntfs_info(EXFAT_INFO) is False


# ---------- volume_from_info ----------

def test_volume_from_info_readonly_mounted():
    v = volume_from_info(NTFS_INFO_RO)
    assert v.device == "/dev/disk4s1"
    assert v.volume_name == "MyPassport"
    assert v.size_bytes == 1_000_204_886_016
    assert v.free_bytes == 322_122_547_200
    assert v.mount_point == "/Volumes/MyPassport"
    assert v.writable is False
    assert v.whole_disk == "/dev/disk4"
    assert v.status == "只读"


def test_volume_from_info_unmounted_unnamed():
    v = volume_from_info(NTFS_INFO_UNMOUNTED)
    assert v.mount_point == ""
    assert v.volume_name == "未命名"
    assert v.status == "未挂载"


def test_volume_from_info_fuse_writable():
    v = volume_from_info(NTFS_INFO_FUSE_RW)
    assert v.writable is True
    assert v.status == "读写"


def test_size_gb_format():
    v = NtfsVolume(
        device="/dev/disk4s1",
        volume_name="X",
        size_bytes=1_000_204_886_016,
        free_bytes=0,
        mount_point="",
        writable=False,
        whole_disk="/dev/disk4",
    )
    assert v.size_gb.endswith("GB")
    assert "931" in v.size_gb  # 1TB 十进制 ≈ 931.5 GiB


# ---------- list_ntfs_volumes ----------

def test_list_ntfs_volumes_filters_non_ntfs():
    vols = list_ntfs_volumes(run=_fake_run_factory(INFO_BY_ID))
    assert len(vols) == 1
    assert vols[0].volume_name == "MyPassport"
    assert vols[0].device == "/dev/disk4s1"


def test_list_ntfs_volumes_empty_when_no_ntfs():
    listing = {
        "AllDisksAndPartitions": [
            {"DeviceIdentifier": "disk1", "Partitions": [{"DeviceIdentifier": "disk1s1"}]},
        ]
    }
    vols = list_ntfs_volumes(
        run=_fake_run_factory({"disk1s1": APFS_INFO}, listing=listing)
    )
    assert vols == []
