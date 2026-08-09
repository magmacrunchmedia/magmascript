"""Shared command runner for local and SSH execution.

Provides a unified interface for running shell commands either locally
(via subprocess) or remotely (via SSH). Used by PIClient and ScoresClient
to avoid duplicating the SSH/local logic.
"""

from __future__ import annotations

import subprocess

from magmascript.core.exceptions import SSHError


class CommandRunner:
    """Execute shell commands locally or via SSH.

    Args:
        host: Remote host (e.g. "192.168.1.16"). Ignored in local mode.
        user: Remote user (e.g. "jake"). Ignored in local mode.
        local: If True, run commands locally via subprocess instead of SSH.
    """

    def __init__(self, host: str, user: str, *, local: bool = False):
        self._host = host
        self._user = user
        self._local = local

    def run(self, cmd: str, *, timeout: int = 15) -> str:
        """Run a shell command. Returns stdout.

        Raises SSHError on connection failure, timeout, or non-zero exit.
        """
        if self._local:
            return self._local_run(cmd, timeout=timeout)
        return self._ssh(cmd, timeout=timeout)

    def _local_run(self, cmd: str, *, timeout: int = 15) -> str:
        """Run a command locally via bash."""
        try:
            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                raise SSHError(
                    f"Command failed (exit {result.returncode}): {stderr or result.stdout.strip()}",
                    host="localhost",
                    code=result.returncode,
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise SSHError("Command timed out", host="localhost")
        except SSHError:
            raise
        except Exception as e:
            raise SSHError(f"Command failed: {e}", host="localhost")

    def _ssh(self, cmd: str, *, timeout: int = 15) -> str:
        """Run a command on the remote host via SSH."""
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

    def rsync(self, local_path: str, remote_path: str, *, delete: bool = True) -> str:
        """Sync files via rsync (remote mode only). Returns stdout.

        Raises SSHError on failure.
        """
        if self._local:
            raise SSHError("rsync is not supported in local mode", host="localhost")
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
