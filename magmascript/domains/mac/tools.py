"""Typed result dataclasses and parsers for the Mac domain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MacSystemInfo:
    """Mac system info, from a single SSH round-trip."""

    hostname: str
    os_version: str
    uptime: str
    cpu_name: str
    cpu_cores: str
    memory: str
    load: str


@dataclass
class MacProcess:
    """One row of the top-processes listing."""

    pid: str
    cpu: str
    mem: str
    command: str


def _format_membytes(raw: str) -> str:
    """hw.memsize is a byte count; show whole gibibytes."""
    try:
        gib = int(raw) / (1024 ** 3)
        return f"{gib:.0f}GB"
    except (ValueError, TypeError):
        return raw


def parse_system_info(text: str) -> MacSystemInfo:
    """Parse the KEY:value block emitted by MacClient.info().

    Expected lines (order-independent, extra lines ignored):
        HOSTNAME:Jake's MacBook Pro
        OS:macOS 26.5.2
        UPTIME:17 days
        CPU:Apple M5 Pro
        CORES:15
        MEMBYTES:25769803776
        LOAD: 1.56 1.76 1.73
    """
    info = {
        "hostname": "", "os": "", "uptime": "",
        "cpu": "", "cores": "", "membytes": "", "load": "",
    }
    for line in text.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.lower().strip()
        if key in info:
            info[key] = val.strip()

    return MacSystemInfo(
        hostname=info["hostname"],
        os_version=info["os"],
        uptime=info["uptime"],
        cpu_name=info["cpu"],
        cpu_cores=info["cores"],
        memory=_format_membytes(info["membytes"]),
        load=info["load"],
    )


def parse_processes(text: str) -> list[MacProcess]:
    """Parse `ps` output: PID %CPU %MEM COMMAND, one process per line.

    The COMMAND column can contain spaces, so only the first three fields are
    split off and the remainder is kept whole.
    """
    procs: list[MacProcess] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, cpu, mem, command = parts
        if not pid.isdigit():          # skips the header row
            continue
        procs.append(MacProcess(pid=pid, cpu=cpu, mem=mem, command=command))
    return procs
