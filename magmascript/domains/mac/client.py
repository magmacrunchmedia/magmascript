"""Mac domain — direct client for a MacBook over SSH.

Same shape as the Pi and MC1 domains: SSH in, run a command, parse the result.
Targets a Mac on the Tailnet (Remote Login enabled, key-based auth). Reuses
CommandRunner so the SSH/local plumbing is not duplicated.
"""

from __future__ import annotations

from magmascript.core.config import Config, get_config
from magmascript.core.runner import CommandRunner
from magmascript.domains.mac.tools import (
    MacProcess,
    MacSystemInfo,
    parse_processes,
    parse_system_info,
)


class MacClient:
    """Direct client for managing a Mac over SSH.

    In remote mode (default), commands run via SSH. In local mode
    (local=True) they run on the local machine — useful when magmascript
    itself is running on the Mac. Raises SSHError on connection or command
    failure.
    """

    def __init__(self, config: Config | None = None, *, local: bool = False):
        cfg = config or get_config()
        self._host = cfg.mac.host
        self._user = cfg.mac.user
        self._local = local
        self._runner = CommandRunner(cfg.mac.host, cfg.mac.user, local=local)

    # ------------------------------------------------------------------
    # System info
    # ------------------------------------------------------------------

    def info(self) -> MacSystemInfo:
        """Hostname, OS, uptime, CPU, cores, memory, and load average.

        Raises SSHError on connection failure.
        """
        stdout = self._runner.run(
            'echo "HOSTNAME:$(scutil --get ComputerName 2>/dev/null || hostname -s)" && '
            'echo "OS:$(sw_vers -productName) $(sw_vers -productVersion)" && '
            'echo "UPTIME:$(uptime | sed \'s/.*up //; s/,[[:space:]]*[0-9]* users.*//\')" && '
            'echo "CPU:$(sysctl -n machdep.cpu.brand_string)" && '
            'echo "CORES:$(sysctl -n hw.ncpu)" && '
            'echo "MEMBYTES:$(sysctl -n hw.memsize)" && '
            'echo "LOAD:$(sysctl -n vm.loadavg | tr -d \'{}\')"'
        )
        return parse_system_info(stdout)

    def processes(self, limit: int = 15) -> list[MacProcess]:
        """Top processes by CPU.

        Raises SSHError on connection failure.
        """
        stdout = self._runner.run(
            f"ps -Aceo pid,pcpu,pmem,comm -r | head -n {limit + 1}"
        )
        return parse_processes(stdout)

    # ------------------------------------------------------------------
    # Git — the reason this domain exists
    # ------------------------------------------------------------------

    def git_status(self, repo: str = "~/Documents/magmascript") -> str:
        """Short branch/tracking status of a repo on the Mac.

        Raises SSHError on connection failure.
        """
        return self._runner.run(f"cd {repo} && git status -sb", timeout=30)

    def git_pull(self, repo: str = "~/Documents/magmascript") -> str:
        """Fast-forward pull a repo on the Mac. Never merges or force-moves.

        Raises SSHError on connection or non-fast-forward failure.
        """
        return self._runner.run(
            f"cd {repo} && git pull --ff-only", timeout=60
        )

    # ------------------------------------------------------------------
    # Arbitrary command
    # ------------------------------------------------------------------

    def run(self, command: str, *, timeout: int = 15) -> str:
        """Run an arbitrary shell command on the Mac and return stdout.

        Raises SSHError on connection failure or non-zero exit.
        """
        return self._runner.run(command, timeout=timeout)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """No-op; SSH connections are per-command."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
