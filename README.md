# klbtoo

Gentoo overlay for [KarpelesLab](https://github.com/KarpelesLab) projects,
built from source with the regular Rust toolchain (`cargo.eclass`).

| Package               | Upstream                                                 |
| --------------------- | -------------------------------------------------------- |
| `dev-libs/purecrypto` | [purecrypto](https://github.com/KarpelesLab/purecrypto) |
| `net-misc/rsurl`      | [rsurl](https://github.com/KarpelesLab/rsurl)           |
| `net-misc/puressh`    | [puressh](https://github.com/KarpelesLab/puressh)       |

## Usage

```sh
eselect repository add klbtoo git https://github.com/KarpelesLab/klbtoo.git
emaint sync -r klbtoo
emerge -av net-misc/rsurl
```

The C libraries and headers are behind `USE=ffi` (`static-libs` adds the
`.a` archives).

## puressh replaces OpenSSH

`net-misc/puressh` installs `ssh`, `scp`, `sftp`, `ssh-add`, `ssh-agent`,
`ssh-keygen`, `ssh-keyscan`, `ssh-copy-id` and (with `USE=server`, the
default) `sshd` under their OpenSSH names, with the `sshd` OpenRC service,
`sshd.service`, `/etc/pam.d/sshd` and `/etc/ssh` configuration, so it blocks
`net-misc/openssh`. This overlay's `virtual/openssh` accepts puressh, so
packages depending on OpenSSH keep working. To switch:

```sh
emerge -av --oneshot net-misc/puressh   # portage removes net-misc/openssh
```

Existing host keys and `sshd_config` in `/etc/ssh` are reused as they are.

## Bumping a package

Packages build from the crates.io release (it ships `Cargo.lock`; the git
tags do not). To move a package to its latest release:

```sh
scripts/bump.py net-misc/rsurl          # or: scripts/bump.py net-misc/rsurl 0.1.22
```

This renames the ebuild, regenerates its `CRATES` block and dependency
`LICENSE+=` line, runs `ebuild manifest` and stages the result in git
(`--keep` keeps the old version). The licenses follow the cargo features
declared on the ebuild's `# bump.py:` line, so update that line when the
ebuild's features or USE flags change.
