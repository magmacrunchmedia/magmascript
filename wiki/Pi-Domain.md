# Pi Domain

The Pi domain provides direct SSH access to the Raspberry Pi for management operations.

## Commands

```bash
# Status and info
magmascript pi status                        # all service statuses
magmascript pi info                          # uptime, memory, temperature
magmascript pi traffic                       # nginx traffic analysis

# Service management
magmascript pi logs <service>                # service logs
magmascript pi logs-errors                   # error logs
magmascript pi logs-today                    # today's logs
magmascript pi restart <service>             # restart a service
magmascript pi restart-all                   # restart all services

# Deployment
magmascript pi deploy <path>                 # deploy files to Pi

# Backup
magmascript pi backup musicbrainz            # backup + commit to GitHub
magmascript pi backup tmdb                   # backup TMDB data

# System
magmascript pi reboot                        # reboot Pi
magmascript pi shutdown                      # shutdown Pi
```

## Configuration

Requires SSH access to the Pi. Set in config.toml:

```toml
[pi]
host = "your-pi-host"
user = "jake"
```

Or environment variables:
- `MAGMA_PI_HOST` — Pi hostname
- `MAGMA_PI_USER` — SSH username

## Python API

```python
from magmascript import PIClient

with PIClient() as pi:
    status = pi.services()
    info = pi.info()
```
