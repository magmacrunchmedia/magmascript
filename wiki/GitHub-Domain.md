# GitHub Domain

The GitHub domain provides direct API access to GitHub operations.

## Commands

```bash
# Workflows
magmascript gh workflows                     # all workflow statuses
magmascript gh workflow <name>               # specific workflow details
magmascript gh trigger "Deploy to Pi"        # trigger a workflow
magmascript gh run <name> [limit]            # workflow run history

# Issues
magmascript gh issues                        # list issues
magmascript gh issue create                  # create an issue
magmascript gh issue close <number>          # close an issue

# Files
magmascript gh file <path>                   # read file from repo

# Pull requests
magmascript gh pr                            # list PRs
magmascript gh pr-create                     # create a PR

# Sync
magmascript gh sync                          # diff + commit all data files
```

## Configuration

Requires `GITHUB_TOKEN` environment variable or `[gh]` section in config.toml:

```toml
[gh]
token = "ghp_..."
owner = "magmacrunchmedia"
repo = "magmacrunch.com"
```

## Python API

```python
from magmascript import GHClient

with GHClient() as gh:
    workflows = gh.workflows()
```
