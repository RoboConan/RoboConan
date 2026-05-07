from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class XorgConan(ConanFile):
    name = "xorg"
    description = "The X.Org project provides an open source implementation of the X Window System."
    license = "MIT"
    homepage = "https://www.x.org/"
    topics = ("xorg", "x11")
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def requirements(self):
        self.requires("libfontenc/[^1.1.9]", transitive_headers=True, transitive_libs=True)
        self.requires("libice/[^1.1.2]", transitive_headers=True, transitive_libs=True)
        self.requires("libsm/[^1.2.6]", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/[^1.8.13]", transitive_headers=True, transitive_libs=True)
        self.requires("libxau/[^1.0.12]", transitive_headers=True, transitive_libs=True)
        self.requires("libxaw/[^1.0.16]", transitive_headers=True, transitive_libs=True)
        self.requires("libxcb/[^1.17.0]", transitive_headers=True, transitive_libs=True)
        self.requires("libxcomposite/[>=0.4.7 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("libxcursor/[^1.2.3]", transitive_headers=True, transitive_libs=True)
        self.requires("libxdamage/[^1.1.7]", transitive_headers=True, transitive_libs=True)
        self.requires("libxdmcp/[^1.1.5]", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/[^1.3.7]", transitive_headers=True, transitive_libs=True)
        self.requires("libxfixes/[^6.0.2]", transitive_headers=True, transitive_libs=True)
        self.requires("libxi/[^1.8.2]", transitive_headers=True, transitive_libs=True)
        self.requires("libxinerama/[^1.1.6]", transitive_headers=True, transitive_libs=True)
        self.requires("libxkbfile/[^1.2.0]", transitive_headers=True, transitive_libs=True)
        self.requires("libxmu/[^1.3.1]", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/[^3.5.19]", transitive_headers=True, transitive_libs=True)
        self.requires("libxrandr/[^1.5.5]", transitive_headers=True, transitive_libs=True)
        self.requires("libxrender/[>=0.9.12 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("libxres/[^1.2.3]", transitive_headers=True, transitive_libs=True)
        self.requires("libxss/[^1.2.5]", transitive_headers=True, transitive_libs=True)
        self.requires("libxt/[^1.3.1]", transitive_headers=True, transitive_libs=True)
        self.requires("libxtst/[^1.2.5]", transitive_headers=True, transitive_libs=True)
        self.requires("libxv/[^1.0.13]", transitive_headers=True, transitive_libs=True)
        self.requires("libxxf86vm/[^1.1.7]", transitive_headers=True, transitive_libs=True)
        self.requires("xcb-util-cursor/[>=0.1.6 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("xcb-util-errors/[^1.0.1]", transitive_headers=True, transitive_libs=True)
        self.requires("xcb-util-image/[>=0.4.1 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("xcb-util-keysyms/[>=0.4.1 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("xcb-util-renderutil/[>=0.3.10 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("xcb-util-wm/[>=0.4.2 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("xcb-util-xrm/[^1.3]", transitive_headers=True, transitive_libs=True)
        self.requires("xcb-util/[>=0.4.1 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("xorg-proto/[>=2024.1]", transitive_headers=True, transitive_libs=True)
        self.requires("xtrans/[^1.5.0]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported.")

    def package_info(self):
        components = {
            "fontenc":        "libfontenc::libfontenc",
            "ice":            "libice::libice",
            "sm":             "libsm::libsm",
            "x11":            "libx11::x11",
            "x11-xcb":        "libx11::x11-xcb",
            "xau":            "libxau::libxau",
            "xaw7":           "libxaw::xaw7",
            "xcb":            "libxcb::xcb",
            "xcb-atom":       "xcb-util::xcb-util",
            "xcb-aux":        "xcb-util::xcb-util",
            "xcb-composite":  "libxcb::xcb-composite",
            "xcb-cursor":     "xcb-util-cursor::xcb-util-cursor",
            "xcb-dri2":       "libxcb::xcb-dri2",
            "xcb-dri3":       "libxcb::xcb-dri3",
            "xcb-errors":     "xcb-util-errors::xcb-util-errors",
            "xcb-event":      "xcb-util::xcb-util",
            "xcb-ewmh":       "xcb-util-wm::xcb-ewmh",
            "xcb-glx":        "libxcb::xcb-glx",
            "xcb-icccm":      "xcb-util-wm::xcb-icccm",
            "xcb-image":      "xcb-util-image::xcb-util-image",
            "xcb-keysyms":    "xcb-util-keysyms::xcb-util-keysyms",
            "xcb-present":    "libxcb::xcb-present",
            "xcb-randr":      "libxcb::xcb-randr",
            "xcb-render":     "libxcb::xcb-render",
            "xcb-renderutil": "xcb-util-renderutil::xcb-util-renderutil",
            "xcb-res":        "libxcb::xcb-res",
            "xcb-shape":      "libxcb::xcb-shape",
            "xcb-shm":        "libxcb::xcb-shm",
            "xcb-sync":       "libxcb::xcb-sync",
            "xcb-util":       "xcb-util::xcb-util",
            "xcb-xfixes":     "libxcb::xcb-xfixes",
            "xcb-xinerama":   "libxcb::xcb-xinerama",
            "xcb-xkb":        "libxcb::xcb-xkb",
            "xcb-xrm":        "xcb-util-xrm::xcb-util-xrm",
            "xcomposite":     "libxcomposite::libxcomposite",
            "xcursor":        "libxcursor::libxcursor",
            "xdamage":        "libxdamage::libxdamage",
            "xdmcp":          "libxdmcp::libxdmcp",
            "xext":           "libxext::libxext",
            "xfixes":         "libxfixes::libxfixes",
            "xi":             "libxi::libxi",
            "xinerama":       "libxinerama::libxinerama",
            "xkbfile":        "libxkbfile::libxkbfile",
            "xmu":            "libxmu::xmu",
            "xmuu":           "libxmu::xmuu",
            "xpm":            "libxpm::libxpm",
            "xproto":         "xorg-proto::xorg-proto",
            "xrandr":         "libxrandr::libxrandr",
            "xrender":        "libxrender::libxrender",
            "xres":           "libxres::libxres",
            "xscrnsaver":     "libxss::libxss",
            "xt":             "libxt::libxt",
            "xtrans":         "xtrans::xtrans",
            "xtst":           "libxtst::libxtst",
            "xv":             "libxv::libxv",
            "xxf86vm":        "libxxf86vm::libxxf86vm",
        }
        for component, require in components.items():
            component = self.cpp_info.components[component]
            component.requires = [require]
            component.bindirs = []
            component.includedirs = []
            component.libdirs = []
