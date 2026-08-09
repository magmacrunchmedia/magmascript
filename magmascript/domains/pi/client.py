"""Pi domain — direct SSH client for Raspberry Pi management.

Bypasses the MCP server for faster, more capable Pi operations.
"""

from __future__ import annotations

import subprocess

from magmascript.core.config import Config, get_config
from magmascript.core.exceptions import SSHError
from magmascript.domains.pi.tools import (
    NginxTraffic,
    PiServiceStatus,
    PiSystemInfo,
    parse_service_list,
    parse_system_info,
)


class PIClient:
    """Direct SSH client for Raspberry Pi management.

    All commands SSH directly to the Pi — no MCP server in the middle.
    Raises SSHError on connection or command failures.
    """

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._host = cfg.pi.host
        self._user = cfg.pi.user

    def _ssh(self, cmd: str, *, timeout: int = 15) -> str:
        """Run a command on the Pi via SSH. Returns stdout.

        Raises SSHError on connection failure, timeout, or non-zero exit.
        """
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "ConnectTimeout=5",
                    "-o", "StrictHostKeyChecking=no",
                    f"{self._user}@{self._host}",
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                raise SSHError(
                    f"SSH command failed (exit {result.returncode}): {stderr or result.stdout.strip()}",
                    host=self._host,
                    code=result.returncode,
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise SSHError(f"SSH connection to {self._host} timed out", host=self._host)
        except SSHError:
            raise
        except Exception as e:
            raise SSHError(f"SSH connection to {self._host} failed: {e}", host=self._host)

    def _rsync(self, local_path: str, remote_path: str, *, delete: bool = True) -> str:
        """Sync files to the Pi via rsync. Returns stdout.

        Raises SSHError on failure.
        """
        cmd = ["rsync", "-avz"]
        if delete:
            cmd.append("--delete")
        cmd.append(local_path)
        cmd.append(f"{self._user}@{self._host}:{remote_path}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise SSHError(
                    f"rsync failed: {result.stderr.strip()}",
                    host=self._host,
                    code=result.returncode,
                )
            return result.stdout.strip()
        except SSHError:
            raise
        except Exception as e:
            raise SSHError(f"rsync to {self._host} failed: {e}", host=self._host)

    # ------------------------------------------------------------------
    # Service management
    # ------------------------------------------------------------------

    def services(self) -> list[PiServiceStatus]:
        """Get status of all arcade services.

        Raises SSHError on connection failure.
        """
        stdout = self._ssh(
            "systemctl list-units --type=service --all --no-legend | grep arcade | awk '{print $1}' | "
            "while read svc; do "
            "name=${svc%.service}; name=${name#arcade-}; "
            "status=$(systemctl is-active $svc 2>/dev/null || echo inactive); "
            "echo \"arcade-$name: $status\"; done"
        )
        return parse_service_list(stdout)

    def logs(self, service: str, lines: int = 50) -> str:
        """Get recent logs for a service.

        Raises SSHError on connection failure.
        """
        unit = service if service.startswith("arcade-") else f"arcade-{service}"
        return self._ssh(f"journalctl -u {unit} -n {lines} --no-pager 2>&1")

    def logs_errors(self, lines: int = 100) -> str:
        """Get error-level logs from all arcade services.

        Raises SSHError on connection failure.
        """
        return self._ssh(
            f"journalctl -u 'arcade-*' -p err -n {lines} --no-pager",
            timeout=15,
        )

    def logs_today(self) -> str:
        """Get today's logs from all arcade services.

        Raises SSHError on connection failure.
        """
        return self._ssh(
            "journalctl -u 'arcade-*' --since today --no-pager",
            timeout=15,
        )

    def restart(self, service: str) -> str:
        """Restart a single service.

        Raises SSHError on connection failure.
        """
        unit = service if service.startswith("arcade-") else f"arcade-{service}"
        self._ssh(f"sudo systemctl restart {unit}", timeout=30)
        return f"✓ {unit} restarted"

    def restart_all(self) -> str:
        """Restart all arcade services.

        Raises SSHError on connection failure.
        """
        self._ssh("sudo systemctl restart 'arcade-*'", timeout=60)
        return "✓ All arcade services restarted"

    # ------------------------------------------------------------------
    # System info
    # ------------------------------------------------------------------

    def info(self) -> PiSystemInfo:
        """Get Pi system info (uptime, hostname, memory, temp, load).

        Raises SSHError on connection failure.
        """
        stdout = self._ssh(
            'echo "UPTIME:$(uptime -p)" && '
            'echo "HOSTNAME:$(hostname)" && '
            'echo "MEMORY:$(free -h | awk \'/^Mem:/ {print $3"/"$2}\')" && '
            'echo "TEMP:$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 | cut -d\'"\' -f1 || echo N/A)" && '
            'echo "LOAD:$(cat /proc/loadavg | awk \'{print $1", "$2", "$3}\')"'
        )
        return parse_system_info(stdout)

    # ------------------------------------------------------------------
    # Nginx traffic
    # ------------------------------------------------------------------

    def traffic(self, lines: int = 1000) -> NginxTraffic:
        """Analyze nginx access logs.

        Raises SSHError on connection failure.
        """
        top_ips = self._ssh(
            f"sudo tail -n {lines} /var/log/nginx/access.log | awk '{{print $1}}' | sort | uniq -c | sort -rn | head -15",
            timeout=15,
        )
        status_codes = self._ssh(
            f"sudo tail -n {lines} /var/log/nginx/access.log | awk '{{print $9}}' | sort | uniq -c | sort -rn",
            timeout=15,
        )
        user_agents = self._ssh(
            f"sudo tail -n {lines} /var/log/nginx/access.log | awk -F'\"' '{{print $6}}' | sort | uniq -c | sort -rn | head -15",
            timeout=15,
        )
        total = self._ssh(
            "sudo wc -l < /var/log/nginx/access.log",
            timeout=15,
        )
        return NginxTraffic(
            top_ips=top_ips,
            status_codes=status_codes,
            user_agents=user_agents,
            total_requests=total,
        )

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def deploy(self, local_path: str, service: str = "") -> str:
        """Deploy files to the Pi via rsync.

        Raises SSHError on connection or rsync failure.
        """
        if "/" in local_path or local_path.endswith(".py") or local_path.endswith(".js"):
            remote = f"{self._host}:~/arcade/"
            self._rsync(local_path, remote, delete=False)
        else:
            remote = f"{self._host}:~/arcade/"
            self._rsync(f"{local_path}/", remote)

        output = f"✓ Deployed {local_path} to Pi"

        if service:
            restart_result = self.restart(service)
            output += f"\n{restart_result}"

        return output

    # ------------------------------------------------------------------
    # Pi power
    # ------------------------------------------------------------------

    def reboot(self) -> str:
        """Reboot the Pi.

        Raises SSHError on connection failure.
        """
        self._ssh("sudo reboot", timeout=10)
        return "✓ Rebooting Pi..."

    def shutdown(self) -> str:
        """Power off the Pi.

        Raises SSHError on connection failure.
        """
        self._ssh("sudo poweroff", timeout=10)
        return "✓ Shutting down Pi..."

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """No-op — SSH doesn't need cleanup."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
