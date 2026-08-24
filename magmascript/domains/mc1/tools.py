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


@dataclass
class MC1PowerSettings:
    """MC1 power management settings."""

    sleep_timeout_ac: int  # minutes (0 = never)
    sleep_timeout_dc: int  # minutes (0 = never)
    hibernate_timeout_ac: int  # minutes (0 = never)
    hibernate_timeout_dc: int  # minutes (0 = never)
    power_mode: str  # "always-on" or "sleep"
    hibernate_enabled: bool = True


# ---------------------------------------------------------------------------
# Uptime formatting
# ---------------------------------------------------------------------------


def _format_uptime(raw: str) -> str:
    """Parse .NET TimeSpan string into human-readable form.

    Two formats from PowerShell:
      >1 day:  '1.03:05:36.7441121'  (dot = day separator)
      <1 day:  '07:33:06.0140847'    (dot = fractional seconds)
    """
    try:
        parts = raw.split(".", 1)
        if ":" in parts[0]:
            # No day component: "07:33:06.0140847"
            time_parts = parts[0].split(":")
            days = 0
        else:
            # Day component: "1.03:05:36.7441121"
            days = int(parts[0]) if parts[0].isdigit() else 0
            time_parts = parts[1].split(":") if len(parts) > 1 else []

        hours = int(time_parts[0]) if len(time_parts) > 0 else 0
        minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
        # Seconds may have fractional part attached: "45.1234567"
        sec_str = time_parts[2].split(".")[0] if len(time_parts) > 2 else "0"
        seconds = int(sec_str) if sec_str.isdigit() else 0

        segments = []
        if days > 0:
            segments.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            segments.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            segments.append(f"{minutes} min{'s' if minutes != 1 else ''}")
        if seconds > 0:
            segments.append(f"{seconds}s")
        if not segments:
            segments.append("0s")

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
    # The PowerShell emits CPU: and DISK:, but the dataclass fields are
    # cpu_load and disk_free. Map the emitted keys to the fields so those two
    # are not silently dropped.
    aliases = {"cpu": "cpu_load", "disk": "disk_free"}
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.lower().strip()
            key = aliases.get(key, key)
            val = val.strip()
            if key in info:
                info[key] = val

    # Format uptime from raw TimeSpan to human-readable
    if info["uptime"]:
        info["uptime"] = _format_uptime(info["uptime"])

    return MC1SystemInfo(**info)


def parse_power_settings(text: str) -> MC1PowerSettings:
    """Parse the output of the power settings command.

    Expected format:
        SLEEP_AC:30
        SLEEP_DC:15
        HIBERNATE_AC:0
        HIBERNATE_DC:0
        POWER_MODE:sleep
        HIBERNATE_ENABLED:True
    """
    info = {
        "sleep_timeout_ac": 30,
        "sleep_timeout_dc": 15,
        "hibernate_timeout_ac": 0,
        "hibernate_timeout_dc": 0,
        "power_mode": "sleep",
        "hibernate_enabled": True,
    }
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.lower().strip()
            val = val.strip()
            if key == "sleep_ac":
                info["sleep_timeout_ac"] = int(val) if val.isdigit() else 0
            elif key == "sleep_dc":
                info["sleep_timeout_dc"] = int(val) if val.isdigit() else 0
            elif key == "hibernate_ac":
                info["hibernate_timeout_ac"] = int(val) if val.isdigit() else 0
            elif key == "hibernate_dc":
                info["hibernate_timeout_dc"] = int(val) if val.isdigit() else 0
            elif key == "power_mode":
                info["power_mode"] = val if val in ("always-on", "sleep") else "sleep"
            elif key == "hibernate_enabled":
                info["hibernate_enabled"] = val.lower() == "true"

    return MC1PowerSettings(**info)
