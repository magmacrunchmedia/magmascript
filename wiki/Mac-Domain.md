# Mac Domain

Direct client for managing a Mac over SSH — a MacBook on the Tailnet with Remote
Login enabled and key-based auth. Same shape as the Pi and MC1 domains.

## Configuration

Add to `~/.config/magmascript/config.toml`:

```toml
[mac]
host = "100.81.70.91"
user = "jakemccoy"
```

Or set environment variables: `MAGMA_MAC_HOST`, `MAGMA_MAC_USER`.

The Mac must accept key-based SSH from the machine running magmascript: enable
Remote Login (System Settings → General → Sharing) and add that machine's public
key to `~/.ssh/authorized_keys` on the Mac.

## Script Usage

```magmascript
info = mac.info()
print(f"{info.hostname} — {info.os_version}, up {info.uptime}")
print(f"{info.cpu_name} ({info.cpu_cores} cores), {info.memory}")

// Keeping a checkout in sync
print(mac.git_status())
mac.git_pull()
```

## CLI Usage

```bash
magmascript mac info                    # hostname, OS, CPU, memory, uptime, load
magmascript mac processes 10            # top 10 processes by CPU
magmascript mac git-status              # git status of the default repo
magmascript mac git-pull                # fast-forward pull the default repo
magmascript mac run "sw_vers"           # arbitrary command
```

## Methods

### System Info

`info()` → `MacSystemInfo` — one SSH round-trip for hostname, OS version,
uptime, CPU, cores, memory, and load average.

`processes(limit=15)` → `list[MacProcess]` — top processes by CPU.

### Git

`git_status(repo="~/Documents/magmascript")` → `str` — `git status -sb` of a repo
on the Mac.

`git_pull(repo="~/Documents/magmascript")` → `str` — fast-forward pull only. Never
merges or force-moves; a non-fast-forward raises rather than creating a merge.

### Arbitrary

`run(command, timeout=15)` → `str` — run any shell command on the Mac, returning
stdout. Raises on a non-zero exit.

## Return Types

### MacSystemInfo

| Field | Type | Description |
|-------|------|-------------|
| `hostname` | `str` | Computer name |
| `os_version` | `str` | e.g. `"macOS 26.5.2"` |
| `uptime` | `str` | e.g. `"17 days, 51 mins"` |
| `cpu_name` | `str` | e.g. `"Apple M5 Pro"` |
| `cpu_cores` | `str` | Logical core count |
| `memory` | `str` | Total RAM in whole GB, e.g. `"24GB"` |
| `load` | `str` | 1/5/15-minute load average |

### MacProcess

| Field | Type | Description |
|-------|------|-------------|
| `pid` | `str` | Process ID |
| `cpu` | `str` | `%CPU` |
| `mem` | `str` | `%MEM` |
| `command` | `str` | Executable name (may contain spaces) |

## Python Library

```python
from magmascript import MacClient

with MacClient() as mac:
    print(mac.info().hostname)
    print(mac.git_status())
```

Pass `local=True` to run against the local machine instead of over SSH — useful
when magmascript itself is running on the Mac.
