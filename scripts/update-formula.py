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
from pathlib import Path
from urllib.request import urlretrieve


PYPI_SOURCE = "https://files.pythonhosted.org/packages/source/m/magmascript"


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_sdist(version: str, dest: Path) -> Path:
    filename = f"magmascript-{version}.tar.gz"
    url = f"{PYPI_SOURCE}/{filename}"
    print(f"Downloading {url} ...")
    path, _ = urlretrieve(url, dest / filename)
    return Path(path)


def resolve_dependencies(version: str, sdist_path: Path) -> list[dict]:
    """Use pip download to resolve all dependencies and return their metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Download the package itself plus all deps as sdists
        # Include [cli] extras for prompt_toolkit and pygments
        subprocess.run(
            [
                sys.executable, "-m", "pip", "download",
                "--no-binary", ":all:",
                "--dest", str(tmpdir),
                f"magmascript[cli]=={version}",
            ],
            check=True,
            capture_output=True,
        )

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

  depends_on "python@3.13"

{resources_str}

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{{bin}}/magmascript --help")
  end
end
'''


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip())
        sys.exit(1)

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
