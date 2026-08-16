"""Typed result dataclasses for the MC1 domain."""

from __future__ import annotations

from dataclasses import dataclass, field


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
    disk_free_gb: str = ""
    cpu_name: str = ""
    cpu_cores: str = ""
    os_version: str = ""


# ---------------------------------------------------------------------------
# Uptime formatting
# ---------------------------------------------------------------------------


def _format_uptime(raw: str) -> str:
    """Parse .NET TimeSpan string (e.g. '1.03:05:36.7441121') into human-readable form.

    Format: 'D.HH:MM:SS.fffffff' → '1 day, 3 hours, 5 minutes'
    """
    try:
        # Split on '.' for days, then ':' for time
        parts = raw.split(".", 1)
        days = int(parts[0]) if parts[0].isdigit() else 0

        if len(parts) > 1:
            time_parts = parts[1].split(":")
            hours = int(time_parts[0]) if len(time_parts) > 0 else 0
            minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
        else:
            hours = 0
            minutes = 0

        segments = []
        if days > 0:
            segments.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            segments.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0 or not segments:
            segments.append(f"{minutes} min{'s' if minutes != 1 else ''}")

        return ", ".join(segments)
    except (ValueError, IndexError):
        return raw


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
        DISK_FREE_GB:776.9GB
        CPU_NAME:AMD Ryzen 7 8700F 8-Core Processor
        CPU_CORES:8
        OS_VERSION:Microsoft Windows 11 Home
    """
    info = {
        "hostname": "", "uptime": "", "memory": "", "cpu_load": "",
        "disk_free": "", "disk_free_gb": "", "cpu_name": "",
        "cpu_cores": "", "os_version": "",
    }
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.lower().strip()
            val = val.strip()
            if key in info:
                info[key] = val

    # Format uptime from raw TimeSpan to human-readable
    if info["uptime"]:
        info["uptime"] = _format_uptime(info["uptime"])

    return MC1SystemInfo(**info)
