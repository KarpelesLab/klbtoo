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

Existing host keys in `/etc/ssh` are reused. sshd serves SFTP itself: a
modified `sshd_config` still pointing `Subsystem sftp` at OpenSSH's
`sftp-server` must be changed to `internal-sftp`.

## Bumping a package

Packages build from the crates.io release (it ships `Cargo.lock`; the git
tags do not). For a new version:

```sh
cd net-misc/rsurl
git mv rsurl-0.1.21.ebuild rsurl-0.1.22.ebuild
../../scripts/crates.py rsurl 0.1.22 ffi   # prints CRATES and dependency licenses
# paste the CRATES block, adjust LICENSE+= if the license list changed
ebuild rsurl-0.1.22.ebuild manifest
```

Pass the cargo features the ebuild enables as the third argument
(`server,pam,agent,ffi` for puressh) so the license list matches the build.
