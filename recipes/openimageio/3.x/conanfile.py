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
    topics = ("vfx", "image", "picture")
    license = "Apache-2.0 AND BSD-3-Clause"
    homepage = "http://www.openimageio.org/"

    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_cuda": [True, False],
        "with_dicom": [True, False],
        "with_ffmpeg": [True, False],
        "with_freetype": [True, False],
        "with_giflib": [True, False],
        "with_hdf5": [True, False],
        "with_libheif": [True, False],
        "with_libjxl": [True, False],
        "with_libpng": [True, False],
        "with_libultrahdr": [True, False],
        "with_libwebp": [True, False],
        "with_opencv": [True, False],
        "with_openjpeg": [True, False],
        "with_openjph": [True, False],
        "with_openvdb": [True, False],
        "with_ptex": [True, False],
        "with_raw": [True, False],
        "with_tbb": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_cuda": False,
        "with_dicom": False,
        "with_ffmpeg": False,
        "with_freetype": False,
        "with_giflib": True,
        "with_hdf5": False,
        "with_libheif": False,
        "with_libjxl": False,
        "with_libpng": True,
        "with_libultrahdr": True,
        "with_libwebp": True,
        "with_opencv": False,
        "with_openjpeg": True,
        "with_openjph": False,
        "with_openvdb": False,
        "with_ptex": False,
        "with_raw": False,
        "with_tbb": True,

        "opencv/*:videoio": True,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.with_cuda:
            del self.settings.cuda.architectures
        else:
            del self.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Required libraries
        self.requires("zlib-ng/[^2.0]")
        self.requires("libtiff/[>=4.5 <5]")
        self.requires("imath/[^3.1.9]", transitive_headers=True)
        self.requires("openexr/[^3.3.3]")
        self.requires("libjpeg-meta/latest")
        self.requires("pugixml/[^1.15]")
        self.requires("tsl-robin-map/[^1.3.0]")
        self.requires("fmt/[>=7]", transitive_headers=True)
        self.requires("opencolorio/[^2.4.2]")

        # Optional libraries
        if self.options.with_libjxl:
            self.requires("libjxl/0.11.1")
        if self.options.with_libpng:
            self.requires("libpng/[~1.6]")
        if self.options.with_freetype:
            self.requires("freetype/[^2.13.2]")
        if self.options.with_hdf5:
            self.requires("hdf5/[^1.8]")
        if self.options.with_opencv:
            self.requires("opencv/[^4.5]")
        if self.options.with_tbb:
            self.requires("onetbb/[>=2021 <2023]")
        if self.options.with_dicom:
            self.requires("dcmtk/[^3.6.8]")
        if self.options.with_ffmpeg:
            self.requires("ffmpeg/[>=6]")
        if self.options.with_giflib:
            self.requires("giflib/[^5.2.1]")
        if self.options.with_libheif:
            self.requires("libheif/[^1.19.5]")
        if self.options.with_raw:
            self.requires("libraw/[>=0.21.3 <1]")
        if self.options.with_openjpeg:
            self.requires("openjpeg/[^2.5.2]")
        if self.options.with_openjph:
            self.requires("openjph/[>=0.16.0 <1]")
        if self.options.with_openvdb:
            self.requires("openvdb/[>=11.0.0]")
        if self.options.with_ptex:
            self.requires("ptex/2.4.2")
        if self.options.with_libwebp:
            self.requires("libwebp/[^1.3.2]")
        if self.options.with_libultrahdr:
            self.requires("libultrahdr/[^1.4.0]")
        if self.options.with_cuda:
            self.cuda.requires("cudart")

        # TODO: Field3D dependency
        # TODO: R3DSDK dependency
        # TODO: Nuke dependency

    def validate(self):
        check_min_cppstd(self, 17)
        if is_msvc_static_runtime(self) and self.options.shared:
            raise ConanInvalidConfiguration("Building shared library with static runtime is not supported!")
        if self.options.with_opencv and not self.dependencies["opencv"].options.videoio:
            raise ConanInvalidConfiguration("-o opencv/*:videoio=True is required for with_opencv=True")
        if self.options.with_cuda:
            self.cuda.validate_settings()

    def build_requirements(self):
        self.build_requires("cmake/[>=3.18.2 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        rmdir(self, "src/cmake/modules")
        save(self, "src/testtex/CMakeLists.txt", "")
        # Inject fmt and tsl-robin-map dependencies
        replace_in_file(self, "src/libutil/CMakeLists.txt",
                        "$<TARGET_NAME_IF_EXISTS:Threads::Threads>",
                        "$<TARGET_NAME_IF_EXISTS:Threads::Threads> fmt::fmt tsl::robin_map")

    def generate(self):
        tc = CMakeToolchain(self)

        # CMake options
        tc.cache_variables["CMAKE_DEBUG_POSTFIX"] = ""  # Needed for 2.3.x.x+ versions
        tc.cache_variables["OIIO_BUILD_TOOLS"] = True
        tc.cache_variables["OIIO_BUILD_TESTS"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_DOCS"] = False
        tc.cache_variables["INSTALL_DOCS"] = False
        tc.cache_variables["INSTALL_FONTS"] = False
        tc.cache_variables["INSTALL_CMAKE_HELPER"] = False
        tc.cache_variables["EMBEDPLUGINS"] = True
        tc.cache_variables["USE_PYTHON"] = False
        tc.cache_variables["USE_EXTERNAL_PUGIXML"] = True
        tc.cache_variables["BUILD_MISSING_FMT"] = False
        tc.cache_variables["OIIO_INTERNALIZE_FMT"] = False
        tc.cache_variables["OIIO_USE_CUDA"] = self.options.with_cuda

        # OIIO CMake files are patched to check USE_* flags to require or not use dependencies
        tc.cache_variables["USE_JPEGTURBO"] = "libjpeg-turbo" in self.dependencies
        tc.cache_variables["USE_JPEG"] = True  # Needed for jpeg.imageio plugin, libjpeg/libjpeg-turbo selection still works
        tc.cache_variables["USE_JXL"] = self.options.with_libjxl
        tc.cache_variables["USE_OPENCOLORIO"] = True
        tc.cache_variables["USE_OPENCV"] = self.options.with_opencv
        tc.cache_variables["USE_TBB"] = self.options.with_tbb
        tc.cache_variables["USE_DCMTK"] = self.options.with_dicom
        tc.cache_variables["USE_FIELD3D"] = False
        tc.cache_variables["USE_GIF"] = self.options.with_giflib
        tc.cache_variables["USE_LIBHEIF"] = self.options.with_libheif
        tc.cache_variables["USE_LIBRAW"] = self.options.with_raw
        tc.cache_variables["USE_OPENVDB"] = self.options.with_openvdb
        tc.cache_variables["USE_PTEX"] = self.options.with_ptex
        tc.cache_variables["USE_R3DSDK"] = False
        tc.cache_variables["USE_NUKE"] = False
        tc.cache_variables["USE_OPENGL"] = False
        tc.cache_variables["USE_QT"] = False
        tc.cache_variables["USE_LIBPNG"] = self.options.with_libpng
        tc.cache_variables["USE_FREETYPE"] = self.options.with_freetype
        tc.cache_variables["USE_LIBWEBP"] = self.options.with_libwebp
        tc.cache_variables["USE_OPENJPEG"] = self.options.with_openjpeg
        tc.cache_variables["USE_OPENJPH"] = self.options.with_openjph

        tc.cache_variables["USE_FFMPEG"] = self.options.with_ffmpeg
        if self.options.with_ffmpeg:
            tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_FFmpeg"] = True
            tc.cache_variables["FFMPEG_VERSION"] = f'"{self.dependencies["ffmpeg"].ref.version}"'

        tc.cache_variables["BUILD_MISSING_ROBINMAP"] = False
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_Robinmap"] = True
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_pugixml"] = True
        tc.cache_variables["ROBINMAP_INCLUDES"] = self.dependencies["tsl-robin-map"].cpp_info.includedirs[0].replace("\\", "/")
        tc.cache_variables["IMATH_INCLUDES"] = self.dependencies["imath"].cpp_info.includedirs[0].replace("\\", "/")
        tc.cache_variables["OPENEXR_INCLUDES"] = self.dependencies["openexr"].cpp_info.includedirs[0].replace("\\", "/")
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_PNG"] = self.options.with_libpng
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_Freetype"] = self.options.with_freetype
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_OpenCV"] = self.options.with_opencv
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_TBB"] = self.options.with_tbb
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_DCMTK"] = self.options.with_dicom
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_GIF"] = self.options.with_giflib
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_Libheif"] = self.options.with_libheif
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_LibRaw"] = self.options.with_raw
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_OpenJPEG"] = self.options.with_openjpeg
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_openjph"] = self.options.with_openjph
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_Ptex"] = self.options.with_ptex
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_WebP"] = self.options.with_libwebp
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_JXL"] = self.options.with_libjxl

        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_libjpeg-turbo"] = "libjpeg-turbo" not in self.dependencies
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_R3DSDK"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Nuke"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_JXL"] = not self.options.with_libjxl

        if self.settings.os == "Linux":
            # Workaround for: https://github.com/conan-io/conan/issues/13560
            # note: should not be needed if CMakeConfigDeps is used
            libdirs_host = [l for dependency in self.dependencies.host.values() for l in dependency.cpp_info.aggregated_components().libdirs]
            tc.cache_variables["CMAKE_BUILD_RPATH"] = ";".join(libdirs_host)

        if self.options.with_libultrahdr:
            tc.cache_variables["LIBUHDR_INCLUDE_DIR"] = self.dependencies["libultrahdr"].cpp_info.includedir.replace("\\", "/")

        # Override variable for internal linking visibility of Imath otherwise not visible
        # in the tools included in the build that consume the library.
        tc.cache_variables["OPENIMAGEIO_IMATH_DEPENDENCY_VISIBILITY"] = "PUBLIC"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("fmt", "cmake_additional_variables_prefixes", ["FMT"])
        deps.set_property("ffmpeg", "cmake_additional_variables_prefixes", ["FFMPEG"])
        deps.set_property("ffmpeg", "cmake_file_name", "FFmpeg")
        deps.set_property("ffmpeg", "cmake_additional_variables_prefixes", ["FFMPEG"])
        deps.set_property("libheif", "cmake_target_name", "heif")
        deps.set_property("libheif", "cmake_additional_variables_prefixes", ["LIBHEIF"])
        deps.set_property("libjxl", "cmake_file_name", "JXL")
        deps.set_property("openexr", "cmake_target_name", "OpenEXR::OpenEXR")
        deps.set_property("openjpeg", "cmake_target_name", "OpenJPEG")
        deps.set_property("openjpeg", "cmake_additional_variables_prefixes", ["OPENJPEG"])
        deps.set_property("openvdb", "cmake_target_name", "OpenVDB")
        deps.set_property("openvdb", "cmake_additional_variables_prefixes", ["OPENVDB"])
        deps.set_property("libultrahdr", "cmake_file_name", "libuhdr")
        deps.set_property("libultrahdr", "cmake_target_name", "libuhdr::libuhdr")
        deps.set_property("tsl-robin-map", "cmake_file_name", "Robinmap")
        deps.set_property("tsl-robin-map", "cmake_additional_variables_prefixes", ["ROBINMAP"])
        if self.dependencies["fmt"].options.header_only:
            deps.set_property("fmt", "cmake_target_name", "fmt::fmt")
        else:
            deps.set_property("fmt", "cmake_target_aliases", ["fmt::fmt-header-only"])
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

    @staticmethod
    def _conan_comp(name):
        return f"openimageio_{name.lower()}"

    def _add_component(self, name):
        component = self.cpp_info.components[self._conan_comp(name)]
        component.set_property("cmake_target_name", f"OpenImageIO::{name}")
        return component

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenImageIO")
        self.cpp_info.set_property("pkg_config_name", "OpenImageIO")

        # OpenImageIO::OpenImageIO_Util
        open_image_io_util = self._add_component("OpenImageIO_Util")
        open_image_io_util.libs = ["OpenImageIO_Util"]
        open_image_io_util.requires = [
            "imath::imath",
            "openexr::openexr",
        ]
        if self.settings.os in ["Linux", "FreeBSD"]:
            open_image_io_util.system_libs.extend(["dl", "m", "pthread"])
        if self.options.with_tbb:
            open_image_io_util.requires.append("onetbb::onetbb")

        # OpenImageIO::OpenImageIO
        open_image_io = self._add_component("OpenImageIO")
        open_image_io.libs = ["OpenImageIO"]
        open_image_io.requires = [
            "openimageio_openimageio_util",
            "zlib-ng::zlib-ng",
            "libtiff::libtiff",
            "pugixml::pugixml",
            "tsl-robin-map::tsl-robin-map",
            "fmt::fmt",
            "imath::imath",
            "openexr::openexr",
            "opencolorio::opencolorio",
        ]

        open_image_io.requires.append("libjpeg-meta::jpeg")
        if self.options.with_libjxl:
            open_image_io.requires += ["libjxl::libjxl", "libjxl::jxl_cms"]
        if self.options.with_libpng:
            open_image_io.requires.append("libpng::libpng")
        if self.options.with_freetype:
            open_image_io.requires.append("freetype::freetype")
        if self.options.with_hdf5:
            open_image_io.requires.append("hdf5::hdf5")
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
        if self.options.with_openjph:
            open_image_io.requires.append("openjph::openjph")
        if self.options.with_openvdb:
            open_image_io.requires.append("openvdb::openvdb")
        if self.options.with_ptex:
            open_image_io.requires.append("ptex::ptex")
        if self.options.with_libwebp:
            open_image_io.requires.append("libwebp::libwebp")
        if self.options.with_libultrahdr:
            open_image_io.requires.append("libultrahdr::libultrahdr")
        if self.options.with_libjxl:
            open_image_io.requires.extend(["libjxl::libjxl", "libjxl::jxl_threads"])
        if self.options.with_cuda:
            open_image_io.requires.append("cudart::cudart_")
        if self.settings.os in ["Linux", "FreeBSD"]:
            open_image_io.system_libs.extend(["dl", "m", "pthread"])

        if not self.options.shared:
            open_image_io.defines.append("OIIO_STATIC_DEFINE")
