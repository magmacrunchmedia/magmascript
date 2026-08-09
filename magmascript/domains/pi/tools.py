"""Typed result dataclasses for the Pi domain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PiServiceStatus:
    """Status of a Pi service."""

    name: str
    unit: str
    status: str  # active, inactive, etc.
    ok: bool
    port: int | None = None


@dataclass
class PiSystemInfo:
    """Raspberry Pi system info."""

    uptime: str
    hostname: str
    memory: str
    cpu_temp: str
    cpu_load: str


@dataclass
class NginxTraffic:
    """Nginx access log analysis."""

    top_ips: str
    status_codes: str
    user_agents: str
    total_requests: str


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_service_list(text: str) -> list[PiServiceStatus]:
    """Parse systemctl list-units output into PiServiceStatus list.

    Expected format (from the fixed MCP command):
        arcade-admin: active
        arcade-chat: active
    """
    results = []
    for line in text.splitlines():
        line = line.strip()
        if ":" not in line or not line.startswith("arcade-"):
            continue
        name, status = line.split(":", 1)
        name = name.strip()
        status = status.strip()
        # Extract short name (arcade-chat -> chat)
        short_name = name.replace("arcade-", "")
        results.append(PiServiceStatus(
            name=short_name,
            unit=name,
            status=status,
            ok=status == "active",
        ))
    return results


def parse_system_info(text: str) -> PiSystemInfo:
    """Parse the output of the combined system info command.

    Expected format:
        UPTIME:up 5 days, 3 hours
        HOSTNAME:magmacrunch-server
        MEMORY:2.1Gi/3.7Gi
        TEMP:45.0
        LOAD: 0.50, 0.60, 0.70
    """
    info = {"uptime": "", "hostname": "", "memory": "", "cpu_temp": "", "cpu_load": ""}
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.lower().strip()
            val = val.strip()
            if key == "uptime":
                info["uptime"] = val
            elif key == "hostname":
                info["hostname"] = val
            elif key == "memory":
                info["memory"] = val
            elif key == "temp":
                info["cpu_temp"] = val
            elif key == "load":
                info["cpu_load"] = val
    return PiSystemInfo(**info)
