# Copyright 2026 Mark Karpeles
# Distributed under the terms of the GNU General Public License v2

EAPI=8

# Overrides ::gentoo's virtual/openssh (higher revision) so that packages
# depending on OpenSSH accept net-misc/puressh in its place.

DESCRIPTION="Virtual for net-misc/openssh and variants, including puressh"

SLOT="0"
KEYWORDS="amd64 arm64"
IUSE="ssl"

RDEPEND="
	|| (
		>=net-misc/openssh-9.3_p1-r1[ssl?]
		>=net-misc/openssh-contrib-9.3_p1[ssl?]
		>=net-misc/pkixssh-14.1.1
		net-misc/puressh
	)"
