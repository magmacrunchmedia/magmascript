"""Typed result dataclasses for the MC1 domain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MC1ServiceStatus:
    """Status of a Windows service."""

    name: str
    status: str
    ok: bool


@dataclass
class MC1SystemInfo:
    """MC1 system info."""

    hostname: str
    uptime: str
    memory: str
    cpu_load: str
    disk_free: str


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_service_list(text: str) -> list[MC1ServiceStatus]:
    """Parse PowerShell Get-Service output into MC1ServiceStatus list.

    Expected format (from the PowerShell command):
        AmdPpkgSvc: Running
        AppIDSvc: Running
    """
    results = []
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            name, status = line.split(":", 1)
            name = name.strip()
            status = status.strip()
            results.append(MC1ServiceStatus(
                name=name,
                status=status,
                ok=status.lower() == "running",
            ))
    return results


def parse_system_info(text: str) -> MC1SystemInfo:
    """Parse the output of the combined system info command.

    Expected format:
        HOSTNAME:MC1
        UPTIME:07:33:06.0140847
        MEMORY:31.7GB/7.6GB
        CPU:4%
        DISK:93.2% free
    """
    info = {"hostname": "", "uptime": "", "memory": "", "cpu_load": "", "disk_free": ""}
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.lower().strip()
            val = val.strip()
            if key == "hostname":
                info["hostname"] = val
            elif key == "uptime":
                info["uptime"] = val
            elif key == "memory":
                info["memory"] = val
            elif key == "cpu":
                info["cpu_load"] = val
            elif key == "disk":
                info["disk_free"] = val
    return MC1SystemInfo(**info)
