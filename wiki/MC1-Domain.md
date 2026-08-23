# MC1 Domain

Direct client for managing a Windows PC (MC1) over SSH with PowerShell.

## Configuration

Add to `~/.config/magmascript/config.toml`:

```toml
[mc1]
host = "100.75.220.87"
user = "magma"
```

Or set environment variables: `MAGMA_MC1_HOST`, `MAGMA_MC1_USER`.

## Script Usage

```magmascript
info = mc1.info()
print(f"CPU: {info.cpu_load}, Memory: {info.memory}")

services = mc1.services()
for svc in services {
    print(f"{svc.name}: {svc.status}")
}
```

## Methods

### Service Management

| Method | Returns | Description |
|--------|---------|-------------|
| `mc1.services()` | `list[MC1ServiceStatus]` | List all running Windows services |
| `mc1.restart(service)` | `str` | Restart a Windows service by name |

### System Info

| Method | Returns | Description |
|--------|---------|-------------|
| `mc1.info()` | `MC1SystemInfo` | Uptime, memory, CPU usage, disk free, CPU name, CPU cores, OS version |
| `mc1.processes()` | `str` | Top 15 processes by CPU usage (raw table) |

### Power Management

| Method | Returns | Description |
|--------|---------|-------------|
| `mc1.reboot()` | `str` | Reboot the PC |
| `mc1.get_power_settings()` | `MC1PowerSettings` | Sleep/hibernate timeouts, power mode |
| `mc1.set_sleep_timeout(minutes)` | `str` | Set AC sleep timeout (0 = never) |
| `mc1.set_hibernate_timeout(minutes)` | `str` | Set AC hibernate timeout (0 = never) |
| `mc1.set_power_mode(mode)` | `str` | `"always-on"` (disables sleep) or `"sleep"` (30min sleep, 60min hibernate) |
| `mc1.disable_fast_startup()` | `str` | Disable Windows fast startup for reliable Wake-on-LAN |

### Wake-on-LAN

| Method | Returns | Description |
|--------|---------|-------------|
| `mc1.wake_on_lan(mac_address)` | `str` | Send Wake-on-LAN magic packet (runs locally via `wakeonlan`) |

## Return Types

### MC1ServiceStatus

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Service name |
| `status` | `str` | `"Running"` |
| `ok` | `bool` | Whether the service is running |

### MC1SystemInfo

| Field | Type | Description |
|-------|------|-------------|
| `hostname` | `str` | Computer name |
| `uptime` | `str` | Uptime string (e.g. `"3.05:22:10"`) |
| `memory` | `str` | Total/used (e.g. `"31.5GB/18.2GB"`) |
| `cpu_load` | `str` | CPU load, percent included (e.g. `"4%"`) |
| `disk_free` | `str` | Disk free percentage (e.g. `"45.2% free"`) |
| `disk_free_gb` | `str` | Disk free in GB (e.g. `"234.5GB"`) |
| `cpu_name` | `str` | CPU model (e.g. `"Intel Core i7-12700K"`) |
| `cpu_cores` | `str` | Number of physical cores |
| `os_version` | `str` | Windows version (e.g. `"Microsoft Windows 11 Pro"`) |

### MC1PowerSettings

| Field | Type | Description |
|-------|------|-------------|
| `sleep_timeout_ac` | `int` | AC sleep timeout in minutes (0 = never) |
| `sleep_timeout_dc` | `int` | DC sleep timeout in minutes |
| `hibernate_timeout_ac` | `int` | AC hibernate timeout in minutes (0 = never) |
| `hibernate_timeout_dc` | `int` | DC hibernate timeout in minutes |
| `hibernate_enabled` | `bool` | Whether hibernation is enabled |
| `power_mode` | `str` | `"always-on"` or `"sleep"` |

## Python Library

```python
from magmascript import MC1Client

with MC1Client() as mc1:
    info = mc1.info()
    services = mc1.services()
    mc1.set_power_mode("always-on")
```
