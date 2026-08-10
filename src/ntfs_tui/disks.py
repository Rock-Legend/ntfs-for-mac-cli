"""磁盘探测：通过 diskutil 的 plist 输出发现 NTFS 卷。"""

from __future__ import annotations

import plistlib
import subprocess
from dataclasses import dataclass


@dataclass
class NtfsVolume:
    device: str        # /dev/disk4s1
    volume_name: str   # 无名为 "未命名"
    size_bytes: int
    free_bytes: int
    mount_point: str   # "" 表示未挂载
    writable: bool     # 当前挂载是否可写
    whole_disk: str    # /dev/disk4

    @property
    def status(self) -> str:
        if not self.mount_point:
            return "未挂载"
        return "读写" if self.writable else "只读"

    @property
    def size_gb(self) -> str:
        return f"{self.size_bytes / 2**30:.1f} GB"

    @property
    def free_gb(self) -> str:
        return f"{self.free_bytes / 2**30:.1f} GB"


def is_ntfs_info(info: dict) -> bool:
    """判断 diskutil info 结果是否为 NTFS 卷。

    经 ntfs-3g 挂载后 FilesystemName 会变为 fusefs，
    但分区 Content 仍是 Windows_NTFS，因此两者都要检查。
    """
    haystack = f"{info.get('FilesystemName', '')} {info.get('Content', '')}".lower()
    return "ntfs" in haystack


def volume_from_info(info: dict) -> NtfsVolume:
    name = (info.get("VolumeName") or "").strip() or "未命名"
    return NtfsVolume(
        device=info.get("DeviceNode", ""),
        volume_name=name,
        size_bytes=int(info.get("TotalSize") or info.get("Size") or 0),
        free_bytes=int(info.get("FreeSpace") or 0),
        mount_point=info.get("MountPoint") or "",
        writable=bool(info.get("WritableVolume", False)),
        whole_disk=info.get("ParentWholeDisk", ""),
    )


def _run_plist(run, cmd: list[str]) -> dict:
    result = run(cmd, capture_output=True)
    if result.returncode != 0:
        return {}
    return plistlib.loads(result.stdout)


def list_ntfs_volumes(run=subprocess.run) -> list[NtfsVolume]:
    """列出系统中所有 NTFS 卷（含未挂载）。"""
    listing = _run_plist(run, ["diskutil", "list", "-plist"])
    identifiers: list[str] = []
    for disk in listing.get("AllDisksAndPartitions", []):
        for part in disk.get("Partitions", []) or []:
            ident = part.get("DeviceIdentifier")
            if ident:
                identifiers.append(ident)
        # 无分区的整盘（少见但存在，如直接格式化的 U 盘）
        if not disk.get("Partitions") and disk.get("DeviceIdentifier"):
            identifiers.append(disk["DeviceIdentifier"])

    volumes = []
    for ident in identifiers:
        info = _run_plist(run, ["diskutil", "info", "-plist", ident])
        if info and is_ntfs_info(info):
            volumes.append(volume_from_info(info))
    return volumes
