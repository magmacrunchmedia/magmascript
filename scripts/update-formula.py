#!/usr/bin/env python3
"""Generate an updated Homebrew formula for magmascript.

Usage:
    python scripts/update-formula.py <version> <formula_path>

Example:
    python scripts/update-formula.py 1.6.0 Formula/magmascript.rb
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
from pathlib import Path
from urllib.request import urlretrieve


PYPI_SOURCE = "https://files.pythonhosted.org/packages/source/m/magmascript"

# The Python the generated formula builds against. Dependencies are resolved by
# whichever interpreter runs this script, and environment markers make that
# choice visible in the output — anyio, for one, requires typing_extensions only
# on `python_version < "3.13"`. Resolving on the wrong version therefore writes a
# formula with a resource list Homebrew will never match, so main() refuses.
FORMULA_PYTHON = "3.13"


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_sdist(version: str, dest: Path, retries: int = 5, delay: int = 15) -> Path:
    filename = f"magmascript-{version}.tar.gz"
    url = f"{PYPI_SOURCE}/{filename}"
    for attempt in range(retries):
        print(f"Downloading {url} (attempt {attempt + 1}/{retries}) ...")
        try:
            path, _ = urlretrieve(url, dest / filename)
            return Path(path)
        except urllib.error.HTTPError as e:
            if e.code == 404 and attempt < retries - 1:
                wait = delay * (2 ** attempt)
                print(f"  Not available yet (404), waiting {wait}s ...")
                time.sleep(wait)
            else:
                raise


def resolve_dependencies(version: str, sdist_path: Path,
                         retries: int = 5, delay: int = 15) -> list[dict]:
    """Use pip download to resolve all dependencies and return their metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Download the package itself plus all deps as sdists.
        # Include [cli] extras for prompt_toolkit and pygments.
        #
        # Retried on the same schedule as download_sdist(). A freshly published
        # version reaches the file CDN before it resolves through the index, so
        # this is the call that fails when the release is only minutes old —
        # download_sdist() succeeds and then this raises a moment later.
        for attempt in range(retries):
            print(f"Resolving dependencies (attempt {attempt + 1}/{retries}) ...")
            result = subprocess.run(
                [
                    sys.executable, "-m", "pip", "download",
                    "--no-binary", ":all:",
                    "--dest", str(tmpdir),
                    f"magmascript[cli]=={version}",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                break
            if attempt < retries - 1:
                wait = delay * (2 ** attempt)
                print(f"  pip download failed, waiting {wait}s ...")
                time.sleep(wait)
            else:
                # Without this the log shows a bare CalledProcessError and the
                # actual reason has to be reproduced by hand.
                sys.stderr.write(result.stdout)
                sys.stderr.write(result.stderr)
                result.check_returncode()

        deps = []
        for tarball in sorted(tmpdir.glob("*.tar.gz")):
            raw_name = tarball.stem  # e.g. "anyio-4.14.2.tar"
            # The stem ends with .tar because the file is *.tar.gz
            # Strip it to get "anyio-4.14.2"
            if raw_name.endswith(".tar"):
                raw_name = raw_name[:-4]
            # Split on last dash to handle names with dashes
            parts = raw_name.rsplit("-", 1)
            if len(parts) == 2:
                pkg_name, pkg_version = parts
            else:
                pkg_name = raw_name
                pkg_version = ""

            # Skip the main package itself
            if pkg_name == "magmascript":
                continue

            deps.append({
                "name": pkg_name,
                "version": pkg_version,
                "sha256": sha256_of_file(tarball),
            })

        return deps


def get_pypi_url(package_name: str, version: str) -> str:
    """Get the sdist URL from PyPI JSON API."""
    import json as json_mod
    from urllib.request import urlopen

    api_url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    try:
        with urlopen(api_url) as resp:
            data = json_mod.loads(resp.read())
            for info in data.get("urls", []):
                if info.get("packagetype") == "sdist":
                    return info["url"]
    except Exception:
        pass
    # Fallback to standard URL pattern
    return f"https://files.pythonhosted.org/packages/source/{package_name[0]}/{package_name}/{package_name}-{version}.tar.gz"


def generate_formula(version: str, main_sha256: str, deps: list[dict]) -> str:
    """Generate the Homebrew formula content."""
    resource_blocks = []
    for dep in deps:
        url = get_pypi_url(dep["name"], dep["version"])
        resource_blocks.append(f'''  resource "{dep["name"]}" do
    url "{url}"
    sha256 "{dep["sha256"]}"
  end''')

    resources_str = "\n\n".join(resource_blocks)

    return f'''class Magmascript < Formula
  include Language::Python::Virtualenv

  desc "Scripting toolkit with domain-first subcommands"
  homepage "https://github.com/magmacrunchmedia/magmascript"
  url "https://files.pythonhosted.org/packages/source/m/magmascript/magmascript-{version}.tar.gz"
  sha256 "{main_sha256}"
  license "MIT"

  depends_on "python@{FORMULA_PYTHON}"

{resources_str}

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{{bin}}/magmascript --help")
  end
end
'''


def check_python_matches_formula() -> None:
    """Refuse to resolve dependencies on the wrong Python."""
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    if running == FORMULA_PYTHON:
        return
    sys.exit(
        "\n".join([
            "This script resolves dependencies with the Python running it, but "
            f"the formula pins python@{FORMULA_PYTHON} and this is Python {running}.",
            "Environment markers differ between the two, so the resource list "
            "would not match what Homebrew builds.",
            f"Re-run with Python {FORMULA_PYTHON}.",
        ])
    )


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip())
        sys.exit(1)

    check_python_matches_formula()

    version = sys.argv[1]
    formula_path = Path(sys.argv[2])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        sdist = download_sdist(version, tmpdir)
        print(f"Downloaded: {sdist.name}")
        main_sha256 = sha256_of_file(sdist)

        print("Resolving dependencies...")
        deps = resolve_dependencies(version, sdist)
        print(f"Found {len(deps)} dependencies:")
        for dep in deps:
            print(f"  {dep['name']}=={dep['version']}")

        formula = generate_formula(version, main_sha256, deps)

        formula_path.parent.mkdir(parents=True, exist_ok=True)
        formula_path.write_text(formula)
        print(f"\nWrote formula to {formula_path}")


if __name__ == "__main__":
    main()
