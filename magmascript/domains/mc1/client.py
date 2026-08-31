"""MC1 domain — direct client for Windows PC management.

Supports SSH (remote) execution mode for managing MC1.
"""

from __future__ import annotations

import subprocess

from magmascript.core.config import Config, get_config
from magmascript.core.runner import CommandRunner
from magmascript.domains.mc1.tools import (
    MC1PowerSettings,
    MC1ServiceStatus,
    MC1SystemInfo,
    parse_power_settings,
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

    def start_service(self, service: str) -> str:
        """Start a Windows service.

        Raises SSHError on connection failure.
        """
        self._runner.run(
            f'powershell -Command "Start-Service -Name \\"{service}\\""',
            timeout=30,
        )
        return f"✓ {service} started"

    def stop_service(self, service: str) -> str:
        """Stop a Windows service.

        Raises SSHError on connection failure.
        """
        self._runner.run(
            f'powershell -Command "Stop-Service -Name \\"{service}\\" -Force"',
            timeout=30,
        )
        return f"✓ {service} stopped"

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
    # Wake-on-LAN
    # ------------------------------------------------------------------

    def wake_on_lan(self, mac_address: str) -> str:
        """Send Wake-on-LAN magic packet to MC1.

        This runs the `wakeonlan` command on the Pi (or local machine).
        The MAC address should be MC1's ethernet adapter MAC.

        Args:
            mac_address: Ethernet MAC address (e.g. "A0:AD:9F:A4:72:97" or "A0-AD-9F-A4-72-97")

        Returns:
            Success message
        """
        # Normalize MAC address format (wakeonlan accepts both : and - separators)
        normalized_mac = mac_address.replace("-", ":")
        subprocess.run(
            ["wakeonlan", normalized_mac],
            capture_output=True,
            timeout=10,
        )
        return f"✓ Wake-on-LAN packet sent to {normalized_mac}"

    # ------------------------------------------------------------------
    # Power management
    # ------------------------------------------------------------------

    def get_power_settings(self) -> MC1PowerSettings:
        """Get MC1 power management settings.

        Raises SSHError on connection failure.
        """
        stdout = self._runner.run(
            'powershell -Command "'
            "$sleep_ac = (powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE).Trim().Split(':')[1].Trim().Split(' ')[0]; "
            "$sleep_dc = (powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLEDC).Trim().Split(':')[1].Trim().Split(' ')[0]; "
            "$hib_ac = (powercfg /query SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE).Trim().Split(':')[1].Trim().Split(' ')[0]; "
            "$hib_dc = (powercfg /query SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLEDC).Trim().Split(':')[1].Trim().Split(' ')[0]; "
            "$hib_enabled = (powercfg /hibernate query).Contains('Hibernate'); "
            "Write-Host \"SLEEP_AC:$sleep_ac\"; "
            "Write-Host \"SLEEP_DC:$sleep_dc\"; "
            "Write-Host \"HIBERNATE_AC:$hib_ac\"; "
            "Write-Host \"HIBERNATE_DC:$hib_dc\"; "
            "Write-Host \"HIBERNATE_ENABLED:$hib_enabled\""
            '"'
        )
        settings = parse_power_settings(stdout)

        # Determine power mode based on sleep timeout
        if settings.sleep_timeout_ac == 0 and settings.hibernate_timeout_ac == 0:
            settings.power_mode = "always-on"
        else:
            settings.power_mode = "sleep"

        return settings

    def set_sleep_timeout(self, minutes: int) -> str:
        """Set sleep timeout on AC power.

        Args:
            minutes: Timeout in minutes (0 = never sleep)

        Raises SSHError on connection failure.
        """
        self._runner.run(
            f'powershell -Command "powercfg /change standby-timeout-ac {minutes}"',
            timeout=15,
        )
        mode = "never sleep" if minutes == 0 else f"sleep after {minutes} minutes"
        return f"✓ AC sleep timeout set to {mode}"

    def set_hibernate_timeout(self, minutes: int) -> str:
        """Set hibernate timeout on AC power.

        Args:
            minutes: Timeout in minutes (0 = never hibernate)

        Raises SSHError on connection failure.
        """
        self._runner.run(
            f'powershell -Command "powercfg /change hibernate-timeout-ac {minutes}"',
            timeout=15,
        )
        mode = "never hibernate" if minutes == 0 else f"hibernate after {minutes} minutes"
        return f"✓ AC hibernate timeout set to {mode}"

    def set_power_mode(self, mode: str) -> str:
        """Set power mode to either 'always-on' or 'sleep'.

        Args:
            mode: "always-on" or "sleep" (with 30-minute default timeout)

        Raises SSHError on connection failure.
        """
        if mode == "always-on":
            self.set_sleep_timeout(0)
            self.set_hibernate_timeout(0)
            return "✓ Power mode set to ALWAYS-ON (sleep disabled)"
        elif mode == "sleep":
            self.set_sleep_timeout(30)
            self.set_hibernate_timeout(60)
            return "✓ Power mode set to SLEEP (30min sleep, 60min hibernate)"
        else:
            raise ValueError(f"Unknown power mode: {mode}. Use 'always-on' or 'sleep'")

    def disable_fast_startup(self) -> str:
        """Disable Windows fast startup for reliable Wake-on-LAN.

        Raises SSHError on connection failure.
        """
        self._runner.run(
            'powershell -Command "powercfg /hibernate on; powercfg /change hibernate-timeout-ac 0"',
            timeout=15,
        )
        return "✓ Fast startup disabled (hibernate file enabled for WoL)"

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
