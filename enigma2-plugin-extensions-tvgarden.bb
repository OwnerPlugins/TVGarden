SUMMARY = "Lululla"
MAINTAINER = "Lululla"
SECTION = "base"
PRIORITY = "required"
LICENSE = "proprietary"

require conf/license/license-gplv2.inc

RDEPENDS:${PN} = "ffmpeg gstplayer exteplayer3 enigma2-plugin-systemplugins-serviceapp"
RRECOMMENDS:${PN} = "ca-certificates python3-yt-dlp"

inherit allarch gitpkgv

SRCREV = "${AUTOREV}"
PV = "1.0+git${SRCPV}"
PKGV = "1.0+git${GITPKGV}"
VER ="1.0"
PR = "r0"

SRC_URI = "git://github.com/OwnerPlugins/TVGarden.git;protocol=https;branch=main"

S = "${WORKDIR}/git"

FILES:${PN} = "/usr/*"

do_install() {
    cp -af --no-preserve=ownership ${S}/usr* ${D}/
}

