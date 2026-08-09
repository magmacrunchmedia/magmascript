"""Pi domain — direct SSH client for Raspberry Pi management.

Bypasses the MCP server for faster, more capable Pi operations.
"""

from __future__ import annotations

import subprocess

from magmascript.core.config import Config, get_config
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
    """

    def __init__(self, config: Config | None = None):
        cfg = config or get_config()
        self._host = cfg.pi.host
        self._user = cfg.pi.user

    def _ssh(self, cmd: str, *, timeout: int = 15) -> dict:
        """Run a command on the Pi via SSH."""
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
            return {
                "ok": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "SSH timed out", "code": -1}
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}

    def _rsync(self, local_path: str, remote_path: str, *, delete: bool = True) -> dict:
        """Sync files to the Pi via rsync."""
        cmd = ["rsync", "-avz"]
        if delete:
            cmd.append("--delete")
        cmd.append(local_path)
        cmd.append(f"{self._user}@{self._host}:{remote_path}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return {
                "ok": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "code": result.returncode,
            }
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}

    # ------------------------------------------------------------------
    # Service management
    # ------------------------------------------------------------------

    def services(self) -> list[PiServiceStatus]:
        """Get status of all arcade services."""
        result = self._ssh(
            "systemctl list-units --type=service --all --no-legend | grep arcade | awk '{print $1}' | "
            "while read svc; do "
            "name=${svc%.service}; name=${name#arcade-}; "
            "status=$(systemctl is-active $svc 2>/dev/null || echo inactive); "
            "echo \"arcade-$name: $status\"; done"
        )
        if not result["ok"]:
            return []
        return parse_service_list(result["stdout"])

    def logs(self, service: str, lines: int = 50) -> str:
        """Get recent logs for a service."""
        unit = service if service.startswith("arcade-") else f"arcade-{service}"
        result = self._ssh(f"journalctl -u {unit} -n {lines} --no-pager 2>&1")
        return result["stdout"] or result["stderr"]

    def logs_errors(self, lines: int = 100) -> str:
        """Get error-level logs from all arcade services."""
        result = self._ssh(
            f"journalctl -u 'arcade-*' -p err -n {lines} --no-pager",
            timeout=15,
        )
        return result["stdout"] or "(no errors)"

    def logs_today(self) -> str:
        """Get today's logs from all arcade services."""
        result = self._ssh(
            "journalctl -u 'arcade-*' --since today --no-pager",
            timeout=15,
        )
        return result["stdout"] or "(no logs today)"

    def restart(self, service: str) -> str:
        """Restart a single service."""
        unit = service if service.startswith("arcade-") else f"arcade-{service}"
        result = self._ssh(f"sudo systemctl restart {unit}", timeout=30)
        if result["ok"]:
            return f"✓ {unit} restarted"
        return f"✗ Failed to restart {unit}: {result['stderr']}"

    def restart_all(self) -> str:
        """Restart all arcade services."""
        result = self._ssh("sudo systemctl restart 'arcade-*'", timeout=60)
        if result["ok"]:
            return "✓ All arcade services restarted"
        return f"✗ Failed to restart all: {result['stderr']}"

    # ------------------------------------------------------------------
    # System info
    # ------------------------------------------------------------------

    def info(self) -> PiSystemInfo:
        """Get Pi system info (uptime, hostname, memory, temp, load)."""
        result = self._ssh(
            'echo "UPTIME:$(uptime -p)" && '
            'echo "HOSTNAME:$(hostname)" && '
            'echo "MEMORY:$(free -h | awk \'/^Mem:/ {print $3"/"$2}\')" && '
            'echo "TEMP:$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 | cut -d\'"\' -f1 || echo N/A)" && '
            'echo "LOAD:$(cat /proc/loadavg | awk \'{print $1", "$2", "$3}\')"'
        )
        return parse_system_info(result["stdout"])

    # ------------------------------------------------------------------
    # Nginx traffic
    # ------------------------------------------------------------------

    def traffic(self, lines: int = 1000) -> NginxTraffic:
        """Analyze nginx access logs."""
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
            top_ips=top_ips["stdout"],
            status_codes=status_codes["stdout"],
            user_agents=user_agents["stdout"],
            total_requests=total["stdout"],
        )

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def deploy(self, local_path: str, service: str = "") -> str:
        """Deploy files to the Pi via rsync."""
        # Determine remote path
        if "/" in local_path or local_path.endswith(".py") or local_path.endswith(".js"):
            # File — sync to ~/arcade/
            remote = f"{self._host}:~/arcade/"
            result = self._rsync(local_path, remote, delete=False)
        else:
            # Directory — sync to ~/arcade/
            remote = f"{self._host}:~/arcade/"
            result = self._rsync(f"{local_path}/", remote)

        if not result["ok"]:
            return f"✗ rsync failed: {result['stderr']}"

        output = f"✓ Deployed {local_path} to Pi"

        if service:
            restart_result = self.restart(service)
            output += f"\n{restart_result}"

        return output

    # ------------------------------------------------------------------
    # Pi power
    # ------------------------------------------------------------------

    def reboot(self) -> str:
        """Reboot the Pi."""
        result = self._ssh("sudo reboot", timeout=10)
        return "✓ Rebooting Pi..."

    def shutdown(self) -> str:
        """Power off the Pi."""
        result = self._ssh("sudo poweroff", timeout=10)
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
