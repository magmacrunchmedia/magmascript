"""MC1 domain — direct client for Windows PC management.

Supports SSH (remote) execution mode for managing MC1.
"""

from __future__ import annotations

from magmascript.core.config import Config, get_config
from magmascript.core.runner import CommandRunner
from magmascript.domains.mc1.tools import (
    MC1ServiceStatus,
    MC1SystemInfo,
    parse_service_list,
    parse_system_info,
)


class MC1Client:
    """Direct client for MC1 Windows PC management.

    Commands run via SSH using PowerShell.
    Raises SSHError on connection or command failures.
    """

    def __init__(self, config: Config | None = None, *, local: bool = False):
        cfg = config or get_config()
        self._host = cfg.mc1.host
        self._user = cfg.mc1.user
        self._local = local
        self._runner = CommandRunner(cfg.mc1.host, cfg.mc1.user, local=local)

    # ------------------------------------------------------------------
    # Service management
    # ------------------------------------------------------------------

    def services(self) -> list[MC1ServiceStatus]:
        """Get status of all running Windows services.

        Raises SSHError on connection failure.
        """
        stdout = self._runner.run(
            'powershell -Command "Get-Service | Where-Object {$_.Status -eq \\"Running\\"} | '
            'Select-Object -Property Name, Status | ForEach-Object { \\"$($_.Name): $($_.Status)\\" }"'
        )
        return parse_service_list(stdout)

    def restart(self, service: str) -> str:
        """Restart a Windows service.

        Raises SSHError on connection failure.
        """
        self._runner.run(
            f'powershell -Command "Restart-Service -Name \\"{service}\\" -Force"',
            timeout=30,
        )
        return f"✓ {service} restarted"

    # ------------------------------------------------------------------
    # System info
    # ------------------------------------------------------------------

    def info(self) -> MC1SystemInfo:
        """Get MC1 system info (uptime, memory, CPU, disk).

        Raises SSHError on connection failure.
        """
        stdout = self._runner.run(
            'powershell -Command "'
            '$os = Get-CimInstance Win32_OperatingSystem; '
            '$cpu = Get-CimInstance Win32_Processor; '
            '$disk = Get-CimInstance Win32_LogicalDisk -Filter \\"DriveType=3\\"; '
            'Write-Host \\"HOSTNAME:$(hostname)\\"; '
            'Write-Host \\"UPTIME:$((Get-Date) - $os.LastBootUpTime)\\"; '
            'Write-Host \\"MEMORY:$([math]::Round($os.TotalVisibleMemorySize/1MB, 1))GB/$([math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB, 1))GB\\"; '
            'Write-Host \\"CPU:$($cpu.LoadPercentage)%\\"; '
            'Write-Host \\"DISK:$([math]::Round($disk.FreeSpace/$disk.Size*100, 1))% free\\"; '
            'Write-Host \\"DISK_FREE_GB:$([math]::Round($disk.FreeSpace/1GB, 1))GB\\"; '
            'Write-Host \\"CPU_NAME:$($cpu.Name)\\"; '
            'Write-Host \\"CPU_CORES:$($cpu.NumberOfCores)\\"; '
            'Write-Host \\"OS_VERSION:$($os.Caption)\\"'
            '"'
        )
        return parse_system_info(stdout)

    # ------------------------------------------------------------------
    # Processes
    # ------------------------------------------------------------------

    def processes(self) -> str:
        """Get top processes on MC1 by CPU usage.

        Raises SSHError on connection failure.
        """
        return self._runner.run(
            'powershell -Command "Get-Process | Sort-Object CPU -Descending | '
            'Select-Object -First 15 Name, CPU, WorkingSet | Format-Table -AutoSize"'
        )

    # ------------------------------------------------------------------
    # Power
    # ------------------------------------------------------------------

    def reboot(self) -> str:
        """Reboot MC1.

        Raises SSHError on connection failure.
        """
        self._runner.run(
            'powershell -Command "Restart-Computer -Force"',
            timeout=10,
        )
        return "✓ Rebooting MC1..."

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """No-op."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
