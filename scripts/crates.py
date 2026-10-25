#!/usr/bin/env python3
"""Print the CRATES block for an ebuild from a crate's Cargo.lock.

usage: scripts/crates.py NAME VERSION [FEATURES]

Downloads NAME-VERSION.crate from crates.io (the published crate carries
Cargo.lock; the git tags do not), then prints:

  - the CRATES="..." block (every registry package in Cargo.lock, the
    package itself included so cargo.eclass unpacks it as ${S});
  - the SPDX license expressions of the dependencies that are linked on
    Linux with the default features plus FEATURES (comma-separated, as the
    ebuild enables them), to be translated into LICENSE+= by hand.
"""

import io
import json
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request

REGISTRY = "registry+https://github.com/rust-lang/crates.io-index"


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    name, version = sys.argv[1:3]
    features = sys.argv[3] if len(sys.argv) == 4 else ""
    url = f"https://crates.io/api/v1/crates/{name}/{version}/download"
    req = urllib.request.Request(url, headers={"User-Agent": "klbtoo-crates.py"})
    data = urllib.request.urlopen(req).read()

    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter="data")
        root = f"{tmp}/{name}-{version}"
        with open(f"{root}/Cargo.lock", "rb") as f:
            lock = tomllib.load(f)

        crates = sorted(
            f"{p['name']}@{p['version']}"
            for p in lock["package"]
            if p.get("source") == REGISTRY
        )
        crates.append(f"{name}@{version}")
        print('CRATES="')
        for c in sorted(set(crates)):
            print(f"\t{c}")
        print('"')

        meta = json.loads(
            subprocess.check_output(
                [
                    "cargo", "metadata", "--format-version", "1", "--locked",
                    "--features", features,
                    "--filter-platform", "x86_64-unknown-linux-gnu",
                    "--manifest-path", f"{root}/Cargo.toml",
                ]
            )
        )
        # Only what the build actually pulls in: walk the resolve graph from
        # the root over normal and build dependencies (not dev-dependencies).
        nodes = {n["id"]: n for n in meta["resolve"]["nodes"]}
        pkgs = {p["id"]: p for p in meta["packages"]}
        seen, todo = set(), [meta["resolve"]["root"]]
        while todo:
            node = nodes[todo.pop()]
            for dep in node["deps"]:
                kinds = {k["kind"] for k in dep["dep_kinds"]}
                if kinds - {"dev"} and dep["pkg"] not in seen:
                    seen.add(dep["pkg"])
                    todo.append(dep["pkg"])
        licenses = {}
        for pid in seen:
            p = pkgs[pid]
            licenses.setdefault(p.get("license") or "?", []).append(p["name"])
        print("\n# dependency licenses (linux):", file=sys.stderr)
        for lic, names in sorted(licenses.items()):
            print(f"#   {lic}: {' '.join(sorted(names))}", file=sys.stderr)


if __name__ == "__main__":
    main()
