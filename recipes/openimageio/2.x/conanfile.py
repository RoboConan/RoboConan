import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime

required_conan_version = ">=2.1"


class OpenImageIOConan(ConanFile):
    name = "openimageio"
    description = (
        "OpenImageIO is a library for reading and writing images, and a bunch "
        "of related classes, utilities, and applications. There is a "
        "particular emphasis on formats and functionality used in "
        "professional, large-scale animation and visual effects work for film."
    )
    license = "Apache-2.0"
    homepage = "http://www.openimageio.org/"
    topics = ("vfx", "image", "picture")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libpng": [True, False],
        "with_freetype": [True, False],
        "with_hdf5": [True, False],
        "with_opencolorio": [True, False],
        "with_opencv": [True, False],
        "with_tbb": [True, False],
        "with_dicom": [True, False],
        "with_ffmpeg": [True, False],
        "with_giflib": [True, False],
        "with_libheif": [True, False],
        "with_raw": [True, False],
        "with_openjpeg": [True, False],
        "with_openvdb": [True, False],
        "with_ptex": [True, False],
        "with_libwebp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_libpng": True,
        "with_freetype": False,
        "with_hdf5": False,
        "with_opencolorio": True,
        "with_opencv": False,
        "with_tbb": True,
        "with_dicom": False,
        "with_ffmpeg": False,
        "with_giflib": True,
        "with_libheif": False,
        "with_raw": False,  # libraw is available under CDDL-1.0 or LGPL-2.1, for this reason it is disabled by default
        "with_openjpeg": True,
        "with_openvdb": False,
        "with_ptex": False,
        "with_libwebp": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["boost"].with_filesystem = True
        self.options["boost"].with_regex = True
        self.options["boost"].with_thread = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Required libraries
        self.requires("zlib-ng/[^2.0]")
        self.requires("boost/[^1.71.0]")
        self.requires("libtiff/[>=4.5 <5]")
        # INFO: https://github.com/AcademySoftwareFoundation/OpenImageIO/blob/v2.5.4.0/src/libOpenImageIO/CMakeLists.txt#L126
        self.requires("imath/[^3.1.9]", transitive_headers=True)
        self.requires("openexr/[^3.3.3]")
        self.requires("libjpeg-meta/latest")
        self.requires("pugixml/[^1.14]")
        self.requires("libsquish/1.15")
        self.requires("tsl-robin-map/[^1.2.1]")
        self.requires("fmt/[>=7]", transitive_headers=True, transitive_libs=True)
        self.requires("bzip2/[^1.0.8]")

        # Optional libraries
        if self.options.with_libpng:
            self.requires("libpng/[~1.6]")
        if self.options.with_freetype:
            self.requires("freetype/[^2.13.2]")
        if self.options.with_hdf5:
            self.requires("hdf5/[^1.8]")
        if self.options.with_opencolorio:
            self.requires("opencolorio/[^2.4.1]")
        if self.options.with_opencv:
            # INFO: https://github.com/AcademySoftwareFoundation/OpenImageIO/blob/v2.5.4.0/src/libOpenImageIO/CMakeLists.txt#L131
            self.requires("opencv/[^4.5]", transitive_headers=True)
        if self.options.with_tbb:
            self.requires("onetbb/[>=2021 <2023]")
        if self.options.with_dicom:
            self.requires("dcmtk/[^3.6.7]")
        if self.options.with_ffmpeg:
            self.requires("ffmpeg/[>=6]")
        # TODO: Field3D dependency
        if self.options.with_giflib:
            self.requires("giflib/[^5.2.1]")
        if self.options.with_libheif:
            self.requires("libheif/[^1.16.2]")
        if self.options.with_raw:
            self.requires("libraw/[>=0.21.2 <1]")
        if self.options.with_openjpeg:
            self.requires("openjpeg/[^2.5.2]")
        if self.options.with_openvdb:
            self.requires("openvdb/[^8.0.1]")
        if self.options.with_ptex:
            self.requires("ptex/2.4.2")
        if self.options.with_libwebp:
            self.requires("libwebp/[^1.3.2]")
        # TODO: R3DSDK dependency
        # TODO: Nuke dependency

    def validate(self):
        check_min_cppstd(self, 14)
        if is_msvc_static_runtime(self) and self.options.shared:
            raise ConanInvalidConfiguration(
                "Building shared library with static runtime is not supported!"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)

        # CMake options
        tc.variables["CMAKE_DEBUG_POSTFIX"] = ""  # Needed for 2.3.x.x+ versions
        tc.variables["OIIO_BUILD_TOOLS"] = True
        tc.variables["OIIO_BUILD_TESTS"] = False
        tc.variables["BUILD_DOCS"] = False
        tc.variables["INSTALL_DOCS"] = False
        tc.variables["INSTALL_FONTS"] = False
        tc.variables["INSTALL_CMAKE_HELPER"] = False
        tc.variables["EMBEDPLUGINS"] = True
        tc.variables["USE_PYTHON"] = False
        tc.variables["USE_EXTERNAL_PUGIXML"] = True
        tc.variables["BUILD_MISSING_FMT"] = False

        # Conan is normally not used for testing, so fixing this option to not build the tests
        tc.variables["BUILD_TESTING"] = False

        # Configure optional dependencies
        # OIIO CMake files are patched to check USE_* flags to require or not use dependencies
        # https://github.com/AcademySoftwareFoundation/OpenImageIO/blob/v2.5.4.0/src/cmake/check_is_enabled.cmake
        tc.variables["USE_JPEGTURBO"] = "turbojpeg" in self.dependencies["libjpeg-meta"].cpp_info.components
        tc.variables["USE_JPEG"] = True  # Needed for jpeg.imageio plugin, libjpeg/libjpeg-turbo selection still works
        tc.variables["USE_HDF5"] = self.options.with_hdf5
        tc.variables["USE_OPENCOLORIO"] = self.options.with_opencolorio
        tc.variables["USE_OPENCV"] = self.options.with_opencv
        tc.variables["USE_TBB"] = self.options.with_tbb
        tc.variables["USE_DCMTK"] = self.options.with_dicom
        tc.variables["USE_FFMPEG"] = self.options.with_ffmpeg
        tc.variables["USE_FIELD3D"] = False
        tc.variables["USE_GIF"] = self.options.with_giflib
        tc.variables["USE_LIBHEIF"] = self.options.with_libheif
        tc.variables["USE_LIBRAW"] = self.options.with_raw
        tc.variables["USE_OPENVDB"] = self.options.with_openvdb
        tc.variables["USE_PTEX"] = self.options.with_ptex
        tc.variables["USE_R3DSDK"] = False
        tc.variables["USE_NUKE"] = False
        tc.variables["USE_OPENGL"] = False
        tc.variables["USE_QT"] = False
        tc.variables["USE_LIBPNG"] = self.options.with_libpng
        tc.variables["USE_FREETYPE"] = self.options.with_freetype
        tc.variables["USE_LIBWEBP"] = self.options.with_libwebp
        tc.variables["USE_OPENJPEG"] = self.options.with_openjpeg
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        if self.settings.os == "Windows":
            for vc_file in ("concrt", "msvcp", "vcruntime"):
                rm(self, f"{vc_file}*.dll", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenImageIO")
        self.cpp_info.set_property("pkg_config_name", "OpenImageIO")

        # OpenImageIO::OpenImageIO_Util
        open_image_io_util = self.cpp_info.components["openimageio_util"]
        open_image_io_util.set_property("cmake_target_name", "OpenImageIO::OpenImageIO_Util")
        open_image_io_util.libs = ["OpenImageIO_Util"]
        open_image_io_util.requires = [
            "boost::filesystem",
            "boost::thread",
            "boost::regex",
            "imath::imath",
            "openexr::openexr",
        ]
        if self.settings.os in ["Linux", "FreeBSD"]:
            open_image_io_util.system_libs.extend(["dl", "m", "pthread"])
        if self.options.with_tbb:
            open_image_io_util.requires.append("onetbb::onetbb")

        # OpenImageIO::OpenImageIO
        open_image_io = self.cpp_info.components["openimageio_"]
        open_image_io.set_property("cmake_target_name", "OpenImageIO::OpenImageIO")
        open_image_io.libs = ["OpenImageIO"]
        open_image_io.requires = [
            "openimageio_util",
            "zlib-ng::zlib-ng",
            "libtiff::tiff",
            "pugixml::pugixml",
            "tsl-robin-map::tsl-robin-map",
            "libsquish::libsquish",
            "fmt::fmt",
            "bzip2::bzip2",
        ]

        open_image_io.requires.append("libjpeg-meta::jpeg")
        if self.options.with_libpng:
            open_image_io.requires.append("libpng::libpng")
        if self.options.with_freetype:
            open_image_io.requires.append("freetype::freetype")
        if self.options.with_hdf5:
            open_image_io.requires.append("hdf5::hdf5")
        if self.options.with_opencolorio:
            open_image_io.requires.append("opencolorio::opencolorio")
        if self.options.with_opencv:
            open_image_io.requires.append("opencv::opencv")
        if self.options.with_dicom:
            open_image_io.requires.append("dcmtk::dcmtk")
        if self.options.with_ffmpeg:
            open_image_io.requires.append("ffmpeg::ffmpeg")
        if self.options.with_giflib:
            open_image_io.requires.append("giflib::giflib")
        if self.options.with_libheif:
            open_image_io.requires.append("libheif::libheif")
        if self.options.with_raw:
            open_image_io.requires.append("libraw::libraw")
        if self.options.with_openjpeg:
            open_image_io.requires.append("openjpeg::openjpeg")
        if self.options.with_openvdb:
            open_image_io.requires.append("openvdb::openvdb")
        if self.options.with_ptex:
            open_image_io.requires.append("ptex::ptex")
        if self.options.with_libwebp:
            open_image_io.requires.append("libwebp::libwebp")
        if self.settings.os in ["Linux", "FreeBSD"]:
            open_image_io.system_libs.extend(["dl", "m", "pthread"])

        if not self.options.shared:
            open_image_io.defines.append("OIIO_STATIC_DEFINE")
