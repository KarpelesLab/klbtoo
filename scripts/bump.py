#!/usr/bin/env python3
"""Bump an overlay package to a new crates.io release.

usage: scripts/bump.py CATEGORY/PN [VERSION] [--keep]

Copies the newest ebuild of CATEGORY/PN to VERSION (default: the latest
stable release on crates.io), rewrites its CRATES block, its LICENSE= line
(the crate's own license) and the dependency LICENSE+= line from that
release, and runs `ebuild manifest`.
The previous ebuild is removed unless --keep is given; giving the current
version regenerates that ebuild in place.

The licenses follow the cargo features the ebuild builds with, declared in
the ebuild on the line just above the LICENSE+= line it rewrites:

    # bump.py: features="agent" ffi="ffi" pam="server,pam"
    LICENSE+=" ..."

`features` is always on; every other key is a USE flag, and licenses only
its features pull in are written as `flag? ( ... )`.
"""

import io
import json
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request
from pathlib import Path

OVERLAY = Path(__file__).resolve().parent.parent
REGISTRY = "registry+https://github.com/rust-lang/crates.io-index"

# SPDX identifier -> Gentoo license name, where they differ.
SPDX = {
    "Apache-2.0 WITH LLVM-exception": "Apache-2.0-with-LLVM-exceptions",
    "BSD-2-Clause": "BSD-2",
    "BSD-3-Clause": "BSD",
    "BSL-1.0": "Boost-1.0",
    "Zlib": "ZLIB",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "klbtoo-bump.py"})
    return urllib.request.urlopen(req).read()


def spdx_to_gentoo(expr):
    """Translate an SPDX expression into a Gentoo LICENSE fragment."""
    tokens = re.findall(r"\(|\)|[^\s()]+", expr.replace("/", " OR "))
    pos = 0

    def atom():
        nonlocal pos
        if tokens[pos] == "(":
            pos += 1
            node = disjunction()
            pos += 1  # ")"
            return node
        name = tokens[pos]
        pos += 1
        if pos < len(tokens) and tokens[pos] == "WITH":
            name = f"{name} WITH {tokens[pos + 1]}"
            pos += 2
        return SPDX.get(name, name)

    def conjunction():
        nonlocal pos
        parts = [atom()]
        while pos < len(tokens) and tokens[pos] == "AND":
            pos += 1
            parts.append(atom())
        return " ".join(sorted(set(parts))) if len(parts) > 1 else parts[0]

    def disjunction():
        nonlocal pos
        parts = [conjunction()]
        while pos < len(tokens) and tokens[pos] == "OR":
            pos += 1
            parts.append(conjunction())
        parts = sorted(set(parts))
        return f"|| ( {' '.join(parts)} )" if len(parts) > 1 else parts[0]

    return disjunction()


def dep_licenses(root, features):
    """Gentoo licenses of the crates linked on Linux with these features."""
    meta = json.loads(
        subprocess.check_output(
            [
                "cargo", "metadata", "--format-version", "1", "--locked",
                "--features", ",".join(features),
                "--filter-platform", "x86_64-unknown-linux-gnu",
                "--manifest-path", f"{root}/Cargo.toml",
            ]
        )
    )
    # Walk the resolve graph from the root over normal and build
    # dependencies (not dev-dependencies).
    nodes = {n["id"]: n for n in meta["resolve"]["nodes"]}
    pkgs = {p["id"]: p for p in meta["packages"]}
    seen, todo = set(), [meta["resolve"]["root"]]
    while todo:
        for dep in nodes[todo.pop()]["deps"]:
            kinds = {k["kind"] for k in dep["dep_kinds"]}
            if kinds - {"dev"} and dep["pkg"] not in seen:
                seen.add(dep["pkg"])
                todo.append(dep["pkg"])
    licenses = set()
    for pid in seen:
        lic = pkgs[pid].get("license")
        if not lic:
            sys.exit(f"{pkgs[pid]['name']}: no license in Cargo.toml, check it by hand")
        licenses.add(spdx_to_gentoo(lic))
    return licenses


def main():
    args = [a for a in sys.argv[1:] if a != "--keep"]
    keep = "--keep" in sys.argv[1:]
    if len(args) not in (1, 2) or "/" not in args[0]:
        sys.exit(__doc__)
    pkgdir = OVERLAY / args[0]
    pn = pkgdir.name

    def vkey(path):
        v = path.stem[len(pn) + 1:]
        return [int(x) if x.isdigit() else x for x in re.split(r"[.-]", v)]

    ebuilds = sorted(pkgdir.glob(f"{pn}-*.ebuild"), key=vkey)
    if not ebuilds:
        sys.exit(f"no ebuild in {pkgdir}")
    old = ebuilds[-1]
    if len(args) == 2:
        version = args[1]
    else:
        info = json.loads(fetch(f"https://crates.io/api/v1/crates/{pn}"))
        version = info["crate"]["max_stable_version"]
    new = pkgdir / f"{pn}-{version}.ebuild"
    text = old.read_text()

    decl = re.search(r"^# bump\.py: (.*)$", text, re.M)
    if not decl:
        sys.exit(f"{old.name}: no '# bump.py:' features line")
    flags = dict(kv.split("=", 1) for kv in shlex.split(decl.group(1)))
    base = [f for f in flags.pop("features", "").split(",") if f]

    data = fetch(f"https://crates.io/api/v1/crates/{pn}/{version}/download")
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter="data")
        root = f"{tmp}/{pn}-{version}"
        with open(f"{root}/Cargo.lock", "rb") as f:
            lock = tomllib.load(f)
        with open(f"{root}/Cargo.toml", "rb") as f:
            own = spdx_to_gentoo(tomllib.load(f)["package"]["license"])
        # Every registry package in Cargo.lock, the package itself included
        # so cargo.eclass unpacks it as ${S}.
        crates = {
            f"{p['name']}@{p['version']}"
            for p in lock["package"]
            if p.get("source") == REGISTRY
        }
        crates.add(f"{pn}@{version}")

        always = dep_licenses(root, base)
        license = sorted(always)
        for flag, feats in flags.items():
            extra = dep_licenses(root, base + feats.split(",")) - always
            if extra:
                license.append(f"{flag}? ( {' '.join(sorted(extra))} )")

    block = "CRATES=\"\n" + "".join(f"\t{c}\n" for c in sorted(crates)) + '"'
    text, n = re.subn(r'^CRATES="[^"]*"', lambda _: block, text, flags=re.M)
    if n != 1:
        sys.exit(f"{old.name}: CRATES block not found")
    text, n = re.subn(r'^LICENSE=".*"$', lambda _: f'LICENSE="{own}"', text, flags=re.M)
    if n != 1:
        sys.exit(f"{old.name}: LICENSE= line not found")
    text, n = re.subn(
        r'^(# bump\.py: .*\n)LICENSE\+=".*"$',
        lambda m: f'{m.group(1)}LICENSE+=" {" ".join(license)}"',
        text,
        flags=re.M,
    )
    if n != 1:
        sys.exit(f"{old.name}: no LICENSE+= line right after '# bump.py:'")

    new.write_text(text)
    if new != old and not keep:
        subprocess.check_call(["git", "rm", "-qf", old.name], cwd=pkgdir)
    subprocess.check_call(["ebuild", new.name, "manifest"], cwd=pkgdir)
    subprocess.check_call(["git", "add", new.name, "Manifest"], cwd=pkgdir)
    print(f"{args[0]}: {old.name} -> {new.name}")


if __name__ == "__main__":
    main()
