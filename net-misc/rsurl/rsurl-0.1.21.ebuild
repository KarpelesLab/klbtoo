# Copyright 2026 Mark Karpeles
# Distributed under the terms of the GNU General Public License v2

EAPI=8

CRATES="
	autocfg@1.5.1
	bitflags@2.13.2
	bumpalo@3.20.3
	bytes@1.12.1
	cacrt@0.1.3
	cc@1.9.0
	cfg-if@1.0.5
	cfg_aliases@0.2.2
	compcol@0.7.6
	find-msvc-tools@0.1.15
	futures-channel@0.3.34
	futures-core@0.3.34
	futures-task@0.3.34
	futures-util@0.3.34
	getrandom@0.2.17
	intl@0.6.4
	itoa@1.0.18
	js-sys@0.3.106
	libc@0.2.191
	log@0.4.34
	memchr@2.8.3
	memoffset@0.9.1
	mio@1.2.4
	nix@0.31.3
	once_cell@1.21.4
	pin-project-lite@0.2.17
	proc-macro2@1.0.107
	psl2@0.1.35
	purecrypto@0.10.2
	puressh@0.2.0
	quote@1.0.47
	ring@0.17.14
	rsurl@0.1.21
	rustls-pemfile@2.2.0
	rustls-pki-types@1.15.1
	rustls-webpki@0.103.16
	rustls@0.23.46
	rustversion@1.0.23
	serde@1.0.229
	serde_core@1.0.229
	serde_derive@1.0.229
	serde_json@1.0.154
	shlex@2.0.1
	slab@0.4.12
	socket2@0.6.5
	subtle@2.6.1
	syn@3.0.9
	tokio-macros@2.7.2
	tokio@1.54.1
	unicode-ident@1.0.27
	untrusted@0.9.0
	wasi@0.11.1+wasi-snapshot-preview1
	wasm-bindgen-futures@0.4.79
	wasm-bindgen-macro-support@0.2.129
	wasm-bindgen-macro@0.2.129
	wasm-bindgen-shared@0.2.129
	wasm-bindgen@0.2.129
	web-sys@0.3.106
	windows-link@0.2.1
	windows-sys@0.52.0
	windows-sys@0.61.2
	windows-targets@0.52.6
	windows_aarch64_gnullvm@0.52.6
	windows_aarch64_msvc@0.52.6
	windows_i686_gnu@0.52.6
	windows_i686_gnullvm@0.52.6
	windows_i686_msvc@0.52.6
	windows_x86_64_gnu@0.52.6
	windows_x86_64_gnullvm@0.52.6
	windows_x86_64_msvc@0.52.6
	zeroize@1.9.1
	zmij@1.0.23
"

RUST_MIN_VER="1.95.0"

inherit cargo

DESCRIPTION="Pure-Rust implementation of curl: library, C FFI and CLI"
HOMEPAGE="https://github.com/KarpelesLab/rsurl"
SRC_URI="${CARGO_CRATE_URIS}"

LICENSE="MIT"
# Dependent crate licenses
LICENSE+=" MIT || ( Apache-2.0 MIT )"
SLOT="0"
KEYWORDS="~amd64 ~arm64"
IUSE="ffi static-libs"
REQUIRED_USE="static-libs? ( ffi )"

DOCS=( README.md CHANGELOG.md )

# The C library is built without a SONAME upstream.
QA_SONAME="usr/lib.*/librsurl\.so"

src_configure() {
	local myfeatures=( $(usev ffi) )
	cargo_src_configure
}

src_compile() {
	# The lib target declares cdylib and staticlib besides rlib, so --lib
	# produces the C libraries (whose API needs the ffi feature).
	cargo_src_compile $(usev ffi --lib) --bin rsurl
}

src_install() {
	local dir=$(cargo_target_dir)
	dobin "${dir}"/rsurl
	doman man/rsurl.1

	if use ffi; then
		dolib.so "${dir}"/librsurl.so
		use static-libs && dolib.a "${dir}"/librsurl.a
		doheader include/rsurl.h
	fi

	einstalldocs
}
