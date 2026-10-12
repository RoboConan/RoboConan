import itertools
import json
import os
import re
import textwrap
from collections import OrderedDict
from functools import cached_property, lru_cache
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.21"  # for cmake_extra_variables


class VtkConan(ConanFile):
    name = "vtk"
    description = ("The Visualization Toolkit (VTK) by Kitware is an open-source,"
                   " freely available software system for 3D computer graphics,"
                   " image processing, and visualization.")
    license = "BSD-3-Clause"
    homepage = "https://www.vtk.org/"
    topics = ("scientific", "image", "processing", "visualization")
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "want_all_modules": [True, False],  # Whether to initialize all module to WANT or NOT_WANT
        ### compile options ###
        "enable_logging": [True, False],
        ### symmetric multiprocessing ###
        "smp_implementation": ["Sequential", "STDThread", "OpenMP", "TBB"],
        "smp_enable_sequential": [True, False],
        "smp_enable_stdthread": [True, False],
        "smp_enable_openmp": [True, False],
        "smp_enable_tbb": [True, False],
        ### debugging ###
        "debug_modules": [True, False],
        "debug_leaks": [True, False],
        ### future proofing ###
        "use_future_bool": [True, False],
        "use_future_const": [True, False],
        ### external deps ###
        "with_alembic": [True, False],
        "with_boost": [True, False],
        "with_catalyst": [True, False],
        "with_cgns": [True, False],
        "with_cocoa": [True, False],
        "with_diy2": [True, False],
        "with_eigen": [True, False],
        "with_exodusII": [True, False],
        "with_expat": [True, False],
        "with_ffmpeg": [True, False],
        "with_fontconfig": [True, False],
        "with_freetype": [True, False],
        "with_gdal": [True, False],
        "with_gl2ps": [True, False],
        "with_h5hut": [True, False],
        "with_hdf5": [True, False],
        "with_ifcopenshell": [True, False],
        "with_ioss": [True, False],
        "with_jpeg": [True, False],
        "with_jsoncpp": [True, False],
        "with_kissfft": [True, False],
        "with_kokkos": [True, False],
        "with_libharu": [True, False],
        "with_liblas": [True, False],
        "with_libproj": [True, False],
        "with_libxml2": [True, False],
        "with_memkind": [True, False],
        "with_metaio": [True, False],
        "with_mpi": [True, False],
        "with_mysql": ["libmysqlclient", "mariadb-connector-c", False],
        "with_netcdf": [True, False],
        "with_octree": [True, False],
        "with_odbc": [True, False],
        "with_onnxruntime": [True, False],
        "with_opencascade": [True, False],
        "with_openslide": [True, False],
        "with_openvdb": [True, False],
        "with_openvr": [True, False],
        "with_openxr": [True, False],
        "with_openusd": [True, False],
        "with_pdal": [True, False],
        "with_png": [True, False],
        "with_postgresql": [True, False],
        "with_qt": [True, False],
        "with_sqlite": [True, False],
        "with_theora": [True, False],
        "with_tiff": [True, False],
        "with_vpic": [True, False],
        "with_viskores": [True, False],
        "with_wayland": [True, False],
        "with_x11": [True, False],
        "with_xdmf2": [True, False],
        "with_xdmf3": [True, False],
        "with_zeromq": [True, False],
    }

    default_options = {
        "shared": False,
        "fPIC": True,
        "want_all_modules": True,
        ### compile options ###
        "enable_logging": True,
        ### symmetric multiprocessing ###
        "smp_implementation": "STDThread",
        "smp_enable_sequential": True,
        "smp_enable_stdthread": True,
        "smp_enable_openmp": True,
        "smp_enable_tbb": False,
        ### debugging ###
        "debug_modules": True,
        "debug_leaks": False,
        ### future proofing ###
        "use_future_bool": False,
        "use_future_const": False,
        ### external deps ###
        "with_alembic": False,
        "with_boost": False,
        "with_catalyst": False,
        "with_cgns": False,
        "with_cocoa": False,
        "with_diy2": False,
        "with_eigen": False,
        "with_exodusII": False,
        "with_expat": False,
        "with_ffmpeg": False,
        "with_fontconfig": False,
        "with_freetype": True,
        "with_gdal": False,
        "with_gl2ps": False,
        "with_h5hut": False,
        "with_hdf5": False,
        "with_ifcopenshell": False,
        "with_ioss": False,
        "with_jpeg": True,
        "with_jsoncpp": True,
        "with_kissfft": False,  # Cannot unvendor by default because non-default datatype=double is required
        "with_kokkos": False,
        "with_libharu": False,
        "with_liblas": False,
        "with_libproj": False,
        "with_libxml2": False,
        "with_memkind": False,
        "with_metaio": True,
        "with_mpi": False,
        "with_mysql": False,
        "with_netcdf": False,
        "with_octree": False,
        "with_odbc": False,
        "with_onnxruntime": False,
        "with_opencascade": False,
        "with_openslide": False,
        "with_openvdb": False,
        "with_openvr": False,
        "with_openxr": False,
        "with_openusd": False,
        "with_pdal": False,
        "with_png": True,
        "with_postgresql": False,
        "with_qt": False,
        "with_sqlite": False,
        "with_theora": False,
        "with_tiff": True,
        "with_vpic": False,
        "with_viskores": False,
        "with_wayland": False,
        "with_x11": False,
        "with_xdmf2": False,
        "with_xdmf3": False,
        "with_zeromq": False,

        "ifcopenshell/*:build_ifcgeom": True,
    }
    # All non-third-party VTK modules are also available as options.
    # e.g. "IOGeoJSON": ["auto", "YES", "WANT", "DONT_WANT", "NO"], etc.
    # See options/<version>.json for the full list of modules.
    # Note that only YES/NO values are validated in the Conan recipe,
    # WANT/DONT_WANT are only checked in the CMake configure step.

    def export(self):
        copy(
            self,
            "*.json",
            src=os.path.join(self.recipe_folder, "options"),
            dst=os.path.join(self.export_folder, "options"),
        )

    @property
    def _modules_from_all_versions(self):
        all_modules = set()
        for options_json in Path(self.recipe_folder, "options").glob("*.json"):
            modules = [m for m in json.loads(options_json.read_text())["flat_external_deps"] if m[0].isupper()]
            all_modules.update(modules)
        return sorted(all_modules)

    def init(self):
        all_modules = self._modules_from_all_versions
        new_options = {mod: ["auto", "YES", "WANT", "DONT_WANT", "NO"] for mod in all_modules}
        new_defaults = {mod: "auto" for mod in all_modules}
        self.options.update(new_options, new_defaults)

    @cached_property
    def _module_ext_deps(self):
        return json.loads(Path(self.recipe_folder, "options", f"{self.version}.json").read_text())["flat_external_deps"]

    @cached_property
    def _module_opt_deps(self):
        return json.loads(Path(self.recipe_folder, "options", f"{self.version}.json").read_text())["optional_external_deps"]

    @cached_property
    def _modules(self):
        return [mod for mod in self._module_ext_deps.keys() if mod[0].isupper()]

    @cached_property
    def _vendored_deps(self):
        return [mod for mod in self._module_ext_deps.keys() if mod[0].islower()]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            # FIXME: System ODBC not found on Windows?
            self.options.with_odbc = False
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_x11
            del self.options.with_wayland
        if not is_apple_os(self):
            del self.options.with_cocoa
        for opt in set(self._modules_from_all_versions) - set(self._modules):
            self.options.rm_safe(opt)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # kissfft - we want the double format (also known as kiss_fft_scalar)
        self.options["kissfft"].datatype = "double"
        self.options["pugixml"].wchar_mode = False
        if self.options.with_boost:
            self.options["boost"].with_serialization = True
            self.options["boost"].with_program_options = True
            self.options["boost"].with_thread = True
            self.options["boost"].with_filesystem = True
            self.options["boost"].with_iostreams = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        del self.info.options.debug_modules

    def requirements(self):
        # These are always required by CommonArchive, CommonCore, CommonMath,
        # CommonDataModel, CommonMisc, IOCore, FiltersCore and FiltersGeneral.
        self.requires("exprtk/[>=0.0.2 <1]")
        self.requires("fast_float/[>=8 <9]")
        # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Common/Core/vtkStringFormatter.h#L43-49
        self.requires("fmt/[>=11 <13]", transitive_headers=True, transitive_libs=True)
        self.requires("libarchive/[^3.7.4]")
        self.requires("lz4/[^1.9.4]")
        # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Common/Core/vtkStringToken.h#L29
        self.requires("nlohmann_json/[^3]", transitive_headers=True)
        self.requires("pugixml/[^1.14]")
        # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/IO/MotionFX/vtkMotionFXCFGGrammar.h#L10-14
        self.requires("taocpp-pegtl/[^2.8.3]", transitive_headers=True)
        self.requires("utfcpp/[^4.0.4]")
        self.requires("xz_utils/[^5.4.5]")
        self.requires("zlib-ng/[^2.0]")

        # kissfft is always required, only replaces the vendored version if enabled.
        # VTK mangles its symbols so not unvendoring it should still not cause conflicts.
        if self.options.with_kissfft:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Common/Math/vtkFFT.h
            self.requires("kissfft/[>=131.1.0]", transitive_headers=True, transitive_libs=True)

        # The project uses modified loguru for logging, which cannot be unvendored

        if self.options.with_alembic:
            self.requires("alembic/[^1.8]")
        if self.options.with_boost:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Infovis/Boost/vtkVariantBoostSerialization.h
            self.requires("boost/[^1.71.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_cgns:
            self.requires("cgns/[^4.3.0]")
        if self.options.with_catalyst:
            self.requires("catalyst/[^2.0]")
        if self.options.with_eigen:
            self.requires("eigen/[>=3.3 <6]")
        if self.options.with_expat:
            self.requires("expat/[>=2.6.2 <3]")
        if self.options.with_ffmpeg:
            self.requires("ffmpeg/[>=6]")
        if self.options.with_fontconfig:
            self.requires("fontconfig/[^2.15.0]")
        if self.options.with_freetype:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Rendering/FreeType/vtkFreeTypeTools.h
            self.requires("freetype/[^2.13.2]", transitive_headers=True, transitive_libs=True)
        if self.options.with_gdal:
            self.requires("gdal/[^3.10.0]")
        if self.options.with_hdf5:
            self.requires("hdf5/[^1.8]")
        if self.options.with_ifcopenshell:
            self.requires("ifcopenshell/[>=0.8 <0.9]")
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")
        if self.options.with_jsoncpp:
            self.requires("jsoncpp/[^1.9.5]")
        if self.options.with_kokkos:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/ThirdParty/viskores/vtkviskores/viskores/viskores/Atomic.h#L291-310
            self.requires("kokkos/[>=3.7 <6]", transitive_headers=True, transitive_libs=True)
        if self.options.with_libharu:
            self.requires("libharu/[^2.4.4]")
        if self.options.with_liblas:
            self.requires("liblas/[^1.8.1]")
        if self.options.with_libproj:
            self.requires("proj/[^9.3.1]")
        if self.options.with_libxml2:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/ThirdParty/libxml2/vtk_libxml2.h.in
            self.requires("libxml2/[^2.12.5]", transitive_headers=True, transitive_libs=True)
        if self.options.with_memkind:
            self.requires("memkind/[>=1.14 <2]")
        if self.options.with_mpi:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/ThirdParty/mpi/vtk_mpi.h.in
            self.requires("openmpi/[^4.1.6]", transitive_headers=True, transitive_libs=True, options={"enable_cxx": True})
        if self.options.with_mysql == "libmysqlclient":
            self.requires("libmysqlclient/[^8.1.0]")
        elif self.options.with_mysql == "mariadb-connector-c":
            self.requires("mariadb-connector-c/[^3.3.3]")
        if self.options.with_netcdf:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/ThirdParty/exodusII/vtkexodusII/include/exodusII.h
            is_public = bool(self.options.with_exodusII)
            self.requires("netcdf/[^4.9.3]", transitive_headers=is_public, transitive_libs=is_public)
        if self.options.with_odbc and self.settings.os != "Windows":
            # odbc is a system lib on Windows
            self.requires("odbc/[^2.3.11]")
        if self.options.with_onnxruntime:
            self.requires("onnxruntime/[^1.22]")
        if self.options.with_opencascade:
            self.requires("opencascade/[^7.6.2]")
        if self.options.with_openslide:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Domains/Microscopy/vtkOpenSlideReader.h
            self.requires("openslide/[^4.0.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_openvdb:
            self.requires("openvdb/[^11.0.0]")
        if self.options.with_openvr:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Rendering/OpenVR/vtkOpenVRModel.h
            self.requires("openvr/[^1.16.8]", transitive_headers=True, transitive_libs=True)
        if self.options.with_openxr:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Rendering/OpenXR/vtkOpenXR.h
            self.requires("openxr/[^1.1]", transitive_headers=True, transitive_libs=True)
        if self.options.with_openusd:
            self.requires("openusd/[>=25.08 <26]")
        if self.options.with_pdal:
            self.requires("pdal/[^2.7.2]")
        if self.options.with_png:
            self.requires("libpng/[~1.6]")
        if self.options.with_postgresql:
            self.requires("libpq/[^17.0]")
        if self.options.with_qt:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/GUISupport/Qt/vtkQWidgetWidget.h
            self.requires("qt/[>=5.15 <7]", transitive_headers=True, transitive_libs=True)
        if self.options.with_sqlite:
            self.requires("sqlite3/[>=3.45.0 <4]")
        if self.options.with_theora:
            self.requires("theora/[^1.1.1]")
        if self.options.with_tiff:
            self.requires("libtiff/[>=4.5 <5]")
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.24]")
            self.requires("xkbcommon/[^1.10]")
        if self.options.get_safe("with_x11"):
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Rendering/OpenGL2/vtkXOpenGLRenderWindow.h
            self.requires("xorg/system", transitive_headers=True, transitive_libs=True)
        if self.options.with_zeromq:
            self.requires("zeromq/[^4.3.5]")
        if self.options.smp_enable_openmp:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Common/Core/SMP/OpenMP/vtkSMPThreadLocalBackend.h
            # '#pragma omp' is not used in any public headers
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self.options.smp_enable_tbb:
            # https://gitlab.kitware.com/vtk/vtk/-/blob/v9.7.1/Common/Core/SMP/TBB/vtkSMPToolsImpl.txx
            self.requires("onetbb/[>=2021]", transitive_headers=True, transitive_libs=True)

        # Missing or unusable package recipes
        # ADIOS2 | adios2::adios2
        # ANARI | anari::anari
        # Conduit | conduit::conduit
        # Dawn v20260421.125655 | Dawn::webgpu_dawn
        # DirectX | DirectX::d3d11 DirectX::dxgi | VTK_USE_WIN32_OPENGL
        # NanoVDB | nanovdb
        # OpenImageDenoise | OpenImageDenoise | VTK_ENABLE_OSPRAY AND VTKOSPRAY_ENABLE_DENOISER
        # OpenTURNS | ${OPENTURNS_LIBRARY}
        # OpenXRRemoting | OpenXR::Remoting
        # OSPRay | ospray::ospray | VTK_ENABLE_OSPRAY
        # VisRTX | VisRTX_DynLoad | VTK_ENABLE_VISRTX
        # Viskores | viskores::cont
        # zSpace | zSpace::zSpace

    def tool_requirements(self):
        if self.options.with_qt:
            self.tool_requires("cmake/[>=3.27 <5]")
            self.tool_requires("qt/<host_version>")

    def validate(self):
        if is_msvc(self) and not self.options.shared:
            # vtkCommonCore.lib(vtkSMPToolsAPI.obj) : error LNK2019: unresolved external symbol
            # "public: bool __cdecl vtk::detail::smp::vtkSMPToolsImpl<1>::IsParallelScope(void)"
            raise ConanInvalidConfiguration(
                "-o shared=False is currently not supported on MSVC due to linker errors. Contributions are welcome!"
            )
        check_min_cppstd(self, 17)

        if self.dependencies["pugixml"].options.wchar_mode:
            raise ConanInvalidConfiguration(f"{self.ref} requires pugixml/*:wchar_mode=False")
        if self.options.with_kissfft and self.dependencies["kissfft"].options.datatype != "double":
            raise ConanInvalidConfiguration(f"{self.ref} requires kissfft/*:datatype=double")
        if self.options.with_qt and not self.dependencies["qt"].options.widgets:
            raise ConanInvalidConfiguration(f"{self.ref} requires qt/*:widgets=True")
        if self.options.with_mpi and not self.dependencies["openmpi"].options.enable_cxx:
            raise ConanInvalidConfiguration(f"{self.ref} requires openmpi/*:enable_cxx=True")

        # Just to check for conflicts
        self._compute_module_values()

    @cached_property
    def _default_state(self):
        return "WANT" if self.options.want_all_modules else "DONT_WANT"

    def _initial_state(self, mod):
        state = self.options.get_safe(mod, self._default_state)
        return self._default_state if state == "auto" else state

    def _validate_modules(self):
        # Compute the set of modules available with the given set of external dependencies and
        # check that no unused dependency options are enabled.
        enabled_deps = {opt.replace("with_", "") for opt, value in self.options.items() if opt.startswith("with_") and str(value) != "False"}
        available_modules = set()
        # kissfft is an unconditional third-party module. Kokkos is selected by
        # the top-level VTK_USE_KOKKOS switch rather than module metadata.
        used_deps = {"kissfft", "kokkos"}
        for mod, deps in self._module_ext_deps.items():
            state = self._initial_state(mod)
            deps = set(deps)
            if state != "NO":
                if enabled_deps.issuperset(deps):
                    available_modules.add(mod)
                    used_deps.update(deps)
                    opt_deps = self._module_opt_deps.get(mod, [])
                    used_deps.update(set(opt_deps) & enabled_deps)
                elif state == "YES":
                    raise ConanInvalidConfiguration(f"Module '{mod}' is missing dependencies: {', '.join(deps - enabled_deps)}")
        unused_deps = enabled_deps - used_deps
        if unused_deps:
            msg = []
            for dep in unused_deps:
                related_requires = set()
                disabled_modules = set()
                for mod, deps in self._module_ext_deps.items():
                    if dep in deps:
                        related_requires |= set(deps) - {dep}
                        if self._initial_state(mod) not in ["WANT", "YES"]:
                            disabled_modules.add(mod)
                msg.append(f"\n  - with_{dep}: also requires {', '.join(related_requires)}")
                if disabled_modules:
                    msg.append(f"; used in disabled {', '.join(disabled_modules)} modules")
            raise ConanInvalidConfiguration(f"Unused dependency options:{''.join(msg)}")
        return available_modules

    @lru_cache
    def _compute_module_values(self):
        def _yes_no(value):
            return "YES" if value else "NO"

        def _maybe(value):
            return self._default_state if value else "NO"

        if self.options.with_qt:
            qt = self.dependencies["qt"].options

        modules = {}
        # The common modules and their dependencies should always be available
        modules["CommonArchive"] = "YES"
        modules["CommonColor"] = "YES"
        modules["CommonComputationalGeometry"] = "YES"
        modules["CommonCore"] = "YES"
        modules["CommonDataModel"] = "YES"
        modules["CommonExecutionModel"] = "YES"
        modules["CommonMath"] = "YES"
        modules["CommonMisc"] = "YES"
        modules["CommonPython"] = "NO"
        modules["CommonSystem"] = "YES"
        modules["CommonTransforms"] = "YES"
        modules["FiltersOpenTURNS"] = "NO"
        modules["IOCore"] = "YES"
        modules["Python"] = "NO"
        modules["GUISupportQtQuick"] = _maybe(self.options.with_qt and qt.opengl != "no" and qt.gui and qt.qtshadertools and qt.qtdeclarative)
        modules["RenderingWebGPU"] = _maybe(self.settings.os == "Emscripten")
        modules["RenderingFreeTypeFontConfig"] = _yes_no(self.options.with_freetype and self.options.with_fontconfig)
        modules["catalyst"] = _yes_no(self.options.with_catalyst)
        modules["cgns"] = _yes_no(self.options.with_cgns)
        modules["conduit"] = "NO"
        modules["diy2"] = _yes_no(self.options.with_diy2)
        modules["eigen"] = _yes_no(self.options.with_eigen)
        modules["exodusII"] = _yes_no(self.options.with_exodusII)
        modules["expat"] = _yes_no(self.options.with_expat)
        modules["exprtk"] = "YES"
        modules["fast_float"] = "YES"
        modules["fides"] = _yes_no(self.options.get_safe("with_adios2"))
        modules["fmt"] = "YES"
        modules["freetype"] = _yes_no(self.options.with_freetype)
        modules["gl2ps"] = _yes_no(self.options.with_gl2ps)
        modules["glad"] = "YES"
        modules["h5hut"] = _yes_no(self.options.with_h5hut)
        modules["hdf5"] = _yes_no(self.options.with_hdf5)
        modules["ioss"] = _yes_no(self.options.with_ioss)
        modules["jpeg"] = _yes_no(self.options.with_jpeg)
        modules["jsoncpp"] = _yes_no(self.options.with_jsoncpp)
        modules["kissfft"] = "YES"
        modules["kwiml"] = "YES"
        modules["libharu"] = _yes_no(self.options.with_libharu)
        modules["libproj"] = _yes_no(self.options.with_libproj)
        modules["libxml2"] = _yes_no(self.options.with_libxml2)
        modules["loguru"] = _yes_no(self.options.enable_logging)
        modules["lz4"] = "YES"
        modules["lzma"] = "YES"
        modules["memkind"] = _yes_no(self.options.with_memkind)
        modules["metaio"] = _yes_no(self.options.with_metaio)
        modules["mpi"] = _yes_no(self.options.with_mpi)
        modules["netcdf"] = _yes_no(self.options.with_netcdf)
        modules["nlohmannjson"] = "YES"
        modules["octree"] = _yes_no(self.options.with_octree)
        modules["ogg"] = _yes_no(self.options.with_theora)
        modules["openvr"] = _yes_no(self.options.with_openvr)
        modules["pegtl"] = "YES"
        modules["png"] = _yes_no(self.options.with_png)
        modules["pugixml"] = "YES"
        modules["qt"] = _yes_no(self.options.with_qt)
        modules["sqlite"] = _yes_no(self.options.with_sqlite)
        modules["theora"] = _yes_no(self.options.with_theora)
        modules["tiff"] = _yes_no(self.options.with_tiff)
        modules["scn"] = "YES"
        modules["token"] = "YES"
        modules["utf8"] = "YES"
        modules["verdict"] = "YES"
        modules["viskores"] = _yes_no(self.options.with_viskores)
        modules["vpic"] = _yes_no(self.options.with_vpic)
        modules["vtkm"] = _yes_no(self.options.with_viskores)
        modules["x11"] = "YES"
        modules["xdmf2"] = _yes_no(self.options.with_xdmf2)
        modules["xdmf3"] = _yes_no(self.options.with_xdmf3 and self.options.with_boost)
        modules["zlib"] = "YES"

        # Validate module options
        available_modules = self._validate_modules()
        for mod in self._modules:
            if mod not in available_modules:
                modules[mod] = "NO"
            elif mod not in modules:
                modules[mod] = self._default_state
            # Allow user to override the computed value
            user_value = self._initial_state(mod)
            if modules[mod] == self._default_state:
                modules[mod] = user_value
            # Raise if the user's value conflicts with the computed value
            elif user_value in ["YES", "NO"] and modules[mod] != user_value:
                raise ConanInvalidConfiguration(
                    f"Option '{mod}={user_value}' conflicts with value '{modules[mod]}' computed from 'with_*' options."
                )
        return modules

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)

        # No need for versions on installed names
        tc.variables["VTK_VERSIONED_INSTALL"] = False
        # Nothing gets installed without this ON at the moment.
        tc.variables["VTK_INSTALL_SDK"] = True

        # TODO: Enable KITs - Quote: "Compiles VTK into a smaller set of libraries."
        # Quote: "Can be useful on platforms where VTK takes a long time to launch due to expensive disk access."
        tc.variables["VTK_ENABLE_KITS"] = False

        # Turn these off for CCI
        tc.variables["VTK_BUILD_TESTING"] = False
        tc.variables["VTK_BUILD_EXAMPLES"] = False
        tc.variables["VTK_BUILD_DOCUMENTATION"] = False
        tc.variables["VTK_BUILD_SPHINX_DOCUMENTATION"] = False

        # TODO: maybe this can be enabled
        tc.variables["VTK_FORBID_DOWNLOADS"] = False

        # Preserve the compiler standard selected by the Conan profile.
        tc.variables["VTK_IGNORE_CMAKE_CXX17_CHECKS"] = True

        tc.variables["VTK_DEBUG_LEAKS"] = self.options.debug_leaks
        tc.variables["VTK_ENABLE_CATALYST"] = self.options.get_safe("with_catalyst", False)
        tc.variables["VTK_ENABLE_LOGGING"] = self.options.enable_logging
        tc.variables["VTK_ENABLE_OSPRAY"] = False
        tc.variables["VTK_ENABLE_VR_COLLABORATION"] = self.options.with_zeromq
        tc.variables["VTK_ENABLE_WEBGPU"] = self.settings.os == "Emscripten"
        tc.variables["VTK_ENABLE_WRAPPING"] = False
        if self.options.with_qt:
            tc.variables["VTK_QT_VERSION"] = Version(self.dependencies["qt"].ref.version).major
        tc.variables["VTK_SMP_ENABLE_OPENMP"] = self.options.smp_enable_openmp
        tc.variables["VTK_SMP_ENABLE_SEQUENTIAL"] = self.options.smp_enable_sequential
        tc.variables["VTK_SMP_ENABLE_STDTHREAD"] = self.options.smp_enable_stdthread
        tc.variables["VTK_SMP_ENABLE_TBB"] = self.options.smp_enable_tbb
        tc.variables["VTK_SMP_IMPLEMENTATION_TYPE"] = self.options.smp_implementation
        tc.variables["VTK_USE_COCOA"] = self.options.get_safe("with_cocoa", False)
        tc.variables["VTK_USE_FUTURE_BOOL"] = self.options.use_future_bool
        tc.variables["VTK_USE_FUTURE_CONST"] = self.options.use_future_const
        tc.variables["VTK_USE_KOKKOS"] = self.options.with_kokkos
        tc.variables["VTK_USE_MEMKIND"] = self.options.with_memkind
        tc.variables["VTK_USE_MPI"] = self.options.with_mpi
        tc.variables["VTK_USE_Wayland"] = (
            self.options.get_safe("with_wayland", False)
            and not self.options.get_safe("with_x11", False)
        )
        tc.variables["VTK_USE_WAYLAND_OPENGL"] = self.options.get_safe("with_wayland", False)
        tc.variables["VTK_USE_TK"] = False  # requires wrap_python
        tc.variables["VTK_USE_X"] = self.options.get_safe("with_x11", False)
        tc.variables["VTK_WRAP_JAVA"] = False
        tc.variables["VTK_WRAP_PYTHON"] = False

        # Skip a try_run() check when cross-compiling
        tc.variables["VTK_REQUIRE_LARGE_FILE_SUPPORT"] = True
        tc.variables["XDMF_REQUIRE_LARGE_FILE_SUPPORT"] = True

        # TODO
        # VTK_ENABLE_VISRTX
        # VTK_USE_OPENGL_DELAYED_LOAD
        # VTK_USE_WIN32_OPENGL
        # VTK_USE_VIDEO_FOR_WINDOWS   for video capture
        # VTK_USE_VIDEO_FOR_WINDOWS_CAPTURE   for video capture
        # VTK_USE_MICROSOFT_MEDIA_FOUNDATION   for video capture (MP4)

        # print out info about why modules are not available
        if self.options.debug_modules:
            tc.variables["VTK_DEBUG_MODULE"] = True
            tc.variables["VTK_DEBUG_MODULE_ALL"] = True
            tc.variables["VTK_DEBUG_MODULE_building"] = True
            tc.variables["VTK_DEBUG_MODULE_enable"] = True
            tc.variables["VTK_DEBUG_MODULE_kit"] = True
            tc.variables["VTK_DEBUG_MODULE_module"] = True
            tc.variables["VTK_DEBUG_MODULE_provide"] = True
            tc.variables["VTK_DEBUG_MODULE_testing"] = True

            self.output.info("Computed module values:")
            for mod, value in sorted(self._compute_module_values().items()):
                self.output.info(f"  {mod}: {value}")

        for mod, value in self._compute_module_values().items():
            tc.variables[f"VTK_MODULE_ENABLE_VTK_{mod}"] = value

        for pkg in self._vendored_deps:
            if pkg in ("viskores", "vtkm"):
                pkg = f"vtk{pkg}"
            tc.variables[f"VTK_MODULE_USE_EXTERNAL_VTK_{pkg}"] = False
        # VTK's copy is patched to consume the FastFloat 8 API. The standalone
        # scnlib/4.0.1 package still uses pre-8 enum constants.
        tc.variables["VTK_MODULE_USE_EXTERNAL_VTK_scn"] = False
        tc.variables["VTK_MODULE_USE_EXTERNAL_VTK_kissfft"] = self.options.with_kissfft
        tc.variables["VTK_USE_EXTERNAL"] = True

        if self.options.with_netcdf:
            tc.variables["NetCDF_HAS_PARALLEL"] = ""
        if self.options.with_libproj:
            tc.variables["LibPROJ_MAJOR_VERSION"] = Version(self.dependencies["proj"].ref.version).major

        # TODO: Remove after fixing https://github.com/conan-io/conan/issues/12012
        # Needed for try_compile() calls with MPI::MPI_CXX to work.
        tc.variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)

        tc.generate()

        deps = CMakeDeps(self)

        # allow newer major versions to be used
        deps.set_property("fast_float", "cmake_config_version_compat", "AnyNewerVersion")
        deps.set_property("fmt", "cmake_config_version_compat", "AnyNewerVersion")
        deps.set_property("qt", "cmake_config_version_compat", "AnyNewerVersion")

        # VTK expects different find_package() filenames and targets (check ThirdParty/LIB/CMakeLists.txt)
        cmake_file_names = {
            "catalyst": "catalyst",
            "expat": "EXPAT",
            "exprtk": "ExprTk",
            "fast_float": "FastFloat",
            "ffmpeg": "FFMPEG",
            "fontconfig": "FontConfig",
            "freetype": "Freetype",
            "gdal": "GDAL",
            "libharu": "LibHaru",
            "libmysqlclient": "MySQL",
            "lz4": "LZ4",
            "mariadb-connector-c": "MySQL",
            "memkind": "MEMKIND",
            "netcdf": "NetCDF",
            "ogg": "OGG",
            "openslide": "OpenSlide",
            "openvr": "OpenVR",
            "openxr": "OpenXR",
            "proj": "LibPROJ",
            "taocpp-pegtl": "PEGTL",
            "theora": "THEORA",
            "xz_utils": "LZMA",
        }
        cmake_target_names = {
            "catalyst": "catalyst::catalyst",
            "eigen": "Eigen3::Eigen3",
            "expat": "EXPAT::EXPAT",
            "exprtk": "ExprTk::ExprTk",
            "fast_float": "FastFloat::fast_float",
            "ffmpeg::avcodec": "FFMPEG::avcodec",
            "ffmpeg::avformat": "FFMPEG::avformat",
            "ffmpeg::avutil": "FFMPEG::avutil",
            "ffmpeg::swresample": "FFMPEG::swresample",
            "ffmpeg::swscale": "FFMPEG::swscale",
            "fontconfig": "FontConfig::FontConfig",
            "freetype": "Freetype::Freetype",
            "gdal": "GDAL::GDAL",
            "libharu": "LibHaru::LibHaru",
            "libmysqlclient": "MySQL::MySQL",
            "lz4": "LZ4::LZ4",
            "mariadb-connector-c": "MySQL::MySQL",
            "memkind": "MEMKIND::MEMKIND",
            "netcdf": "NetCDF::NetCDF",
            "ogg": "OGG::OGG",
            "openslide": "OpenSlide::OpenSlide",
            "openvr": "OpenVR::OpenVR",
            "openxr": "OpenXR::OpenXR",
            "proj": "LibPROJ::LibPROJ",
            "taocpp-pegtl": "PEGTL::PEGTL",
            "theora": "THEORA::THEORA",
            "theora::theoradec": "THEORA::DEC",
            "theora::theoraenc": "THEORA::ENC",
            "utfcpp": "utf8cpp::utf8cpp",
            "xz_utils": "LZMA::LZMA",
        }
        for dep, file_name in cmake_file_names.items():
            deps.set_property(dep, "cmake_file_name", file_name)
        for dep, target_name in cmake_target_names.items():
            deps.set_property(dep, "cmake_target_name", target_name)

        deps.set_property("ifcopenshell::IfcParse", "cmake_target_name", "IfcOpenShell::IfcParse")
        deps.set_property("ifcopenshell::IfcGeom", "cmake_target_name", "IfcOpenShell::IfcGeom")
        deps.set_property("liblas", "cmake_additional_variables_prefixes", ["libLAS"])

        deps.generate()
        PkgConfigDeps(self).generate()

        # Store a mapping from CMake to Conan targets for later use in package_info()
        targets_map = self._get_cmake_to_conan_targets_map(deps)
        save(self, self._cmake_targets_map_json, json.dumps(targets_map, indent=2))

    @property
    def _cmake_targets_map_json(self):
        return os.path.join(self.generators_folder, "cmake_to_conan_targets.json")

    @cached_property
    def _cmake_targets_map(self):
        return json.loads(load(self, self._cmake_targets_map_json))

    def _get_cmake_to_conan_targets_map(self, deps):
        """
        Returns a dict of Conan targets corresponding to generated CMake targets. E.g.:
         'WebP::webpdecoder': 'libwebp::webpdecoder',
         'WebP::webpdemux': 'libwebp::webpdemux',
         'ZLIB::ZLIB': 'zlib-ng::zlib-ng',
        """
        def _get_targets(*args):
            targets = [deps.get_property("cmake_target_name", *args),
                       deps.get_property("cmake_module_target_name", *args)]
            targets += deps.get_property("cmake_target_aliases", *args) or []
            return list(filter(None, targets))

        cmake_targets_map = {}
        for req, dependency in self.dependencies.host.items():
            dep_name = req.ref.name
            for target in _get_targets(dependency):
                cmake_targets_map[target] = f"{dep_name}::{dep_name}"
            for component, _ in dependency.cpp_info.components.items():
                for target in _get_targets(dependency, component):
                    cmake_targets_map[target] = f"{dep_name}::{component}"

        # System recipes need special handling since they rely on CMake's Find<Package> modules
        cmake_targets_map.update({
            "JPEG::JPEG": "libjpeg-meta::libjpeg-meta",
            "OpenMP::OpenMP_C": "openmp::openmp",
            "OpenMP::OpenMP_CXX": "openmp::openmp",
            "OpenGL::EGL": "egl::egl",
            "OpenGL::GL": "opengl::opengl",
            "OpenGL::GLES2": "opengl::opengl",
            "OpenGL::GLES3": "opengl::opengl",
            "OpenGL::GLU": "glu::glu",
            "OpenGL::GLX": "opengl::opengl",
            "OpenGL::OpenGL": "opengl::opengl",
            "X11::X11": "xorg::x11",
            "X11::Xcursor": "xorg::xcursor",
            "WAYLAND::Client": "wayland::wayland-client",
            "WAYLAND::Cursor": "wayland::wayland-cursor",
            "XKBCOMMON::xkbcommon": "xkbcommon::libxkbcommon",
        })
        return cmake_targets_map

    def _patch_kissfft(self):
        if self.options.with_kissfft:
            # Using external kissfft, fix includes
            # strict=False to cope with no_copy_source=True
            replace_in_file(self, os.path.join(self.source_folder, "Common", "Math", "vtkFFT.h"),
                            "tools/kiss_fftr.h", "kiss_fftr.h", strict=False)
            # MomentInvariants is downloaded and only available after cmake.configure()
            path = os.path.join(self.source_folder, "Remote", "MomentInvariants", "MomentInvariants", "vtkComputeMoments.cxx")
            if os.path.exists(path):
                replace_in_file(self, path, "tools/kiss_fftnd.h", "kiss_fftnd.h")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self._patch_kissfft()
        cmake.build()

    def _parse_cmake_targets(self, targets_file):
        # Parse info from VTK-targets.cmake
        # Example:
        #   add_library(VTK::IOOggTheora SHARED IMPORTED)
        #   set_target_properties(VTK::IOOggTheora PROPERTIES
        #   INTERFACE_COMPILE_DEFINITIONS "VTK_HAS_OGGTHEORA_SUPPORT"
        #   INTERFACE_INCLUDE_DIRECTORIES "${_IMPORT_PREFIX}/include/vtk"
        #   INTERFACE_LINK_LIBRARIES "VTK::CommonExecutionModel;VTK::IOMovie"
        #   )
        # The following properties are set by the project:
        #   compile_definitions
        #   compile_features (only sets CXX_STANDARD)
        #   include_directories (always "${_IMPORT_PREFIX}/include/vtk")
        #   link_libraries
        #   system_include_directories (still include/vtk, but silent)
        txt = Path(targets_file).read_text("utf8")
        raw_targets = re.findall(r"add_library\(VTK::(\S+) (\S+) IMPORTED\)", txt)
        targets = {name: {"is_interface": kind == "INTERFACE"} for name, kind in raw_targets if name not in ["vtkbuild"]}
        props_raw = re.findall(r"set_target_properties\(VTK::(\S+) PROPERTIES\n((?: *.+\n)+)\)", txt)
        for name, body in props_raw:
            for prop, value in re.findall(r"^ *INTERFACE_(\w+)\b \"(.+)\"$", body, re.M):
                value = value.split(";")
                targets[name][prop.lower()] = value
        return targets

    @staticmethod
    def _strip_prefix(name):
        if name.startswith("VTK::"):
            return name[5:]
        return name

    def _get_info_from_modules_json(self, modules_json):
        modules = json.loads(load(self, modules_json))["modules"]
        return {
            self._strip_prefix(module): {
                "deps": list(map(self._strip_prefix, mod_info.get("depends", []) + mod_info.get("private_depends", []))),
                "lib_name": mod_info.get("library_name"),
                "implementable": mod_info.get("implementable", False),
                "implements": list(map(self._strip_prefix, mod_info.get("implements", []))),
            }
            for module, mod_info in modules.items()
        }

    def _is_matching_cmake_platform(self, platform_id):
        if platform_id == "Darwin":
            return is_apple_os(self)
        if platform_id == "Linux":
            return self.settings.os in ["Linux", "FreeBSD"]
        if platform_id in ["WIN32", "Windows"]:
            return self.settings.os == "Windows"
        if platform_id == "MinGW":
            return self.settings.os == "Windows" and self.settings.compiler == "gcc"
        if platform_id in ["Android", "Emscripten", "SunOS"]:
            return self.settings.os == platform_id
        raise ConanException(f"Unexpected CMake PLATFORM_ID: '{platform_id}'")

    def _cmake_target_to_conan_requirement(self, target):
        if target.startswith("VTK::"):
            # Internal target
            return target[5:]
        else:
            # External target
            req = self._cmake_targets_map.get(target, target)
            if not req:
                raise ConanException(f"Unexpected CMake target: '{target}'")
            return req

    @property
    def _known_system_libs(self):
        # System libraries used by VTK or its vendored dependencies
        return [
            "m", "dl", "pthread", "rt", "socket", "nsl", "execinfo", # Linux/FreeBSD
            "android", "log", # Android
            "embind", # Emscripten
            "ws2_32", "wsock32", "dbghelp", "psapi", "opengl32", "comctl32", "import32", # Windows
        ]

    def _transform_link_libraries(self, values):
        # Converts a list of LINK_LIBRARIES values into a list of component requirements, system_libs and frameworks.
        requires = []
        system_libs = []
        frameworks = []
        for v in values:
            # strip "\$<LINK_ONLY:FontConfig::FontConfig>" etc.
            v = re.sub(r"^\\\$<(?:LINK_ONLY|COMPILE_ONLY):(.*)>$", r"\1", v)
            if not v:
                continue
            if "-framework " in v:
                frameworks += re.findall(r"-framework (\S+)", v)
            elif "PLATFORM_ID" in v:
                # e.g. "\$<\$<PLATFORM_ID:WIN32>:wsock32>"
                platform_id = re.search(r"PLATFORM_ID:(\w+)", v).group(1)
                if self._is_matching_cmake_platform(platform_id):
                    lib = re.search(r":(\w+)>$", v).group(1)
                    system_libs.append(lib)
            elif v.lower().replace(".lib", "") in self._known_system_libs:
                system_libs.append(v)
            elif v == "Threads::Threads":
                if self.settings.os in ["Linux", "FreeBSD"]:
                    system_libs.append("pthread")
            else:
                # vtkm is the only internal dependency that does not use the VTK:: prefix
                requires = [r for r in requires if not r.startswith("vtkm::")]
                requires.append(self._cmake_target_to_conan_requirement(v))
        return requires, system_libs, frameworks

    @property
    def _lib_suffix(self):
        return "d" if self.settings.os == "Windows" and self.settings.build_type == "Debug" else ""

    @staticmethod
    def _remove_duplicates(values):
        return list(OrderedDict.fromkeys(values))

    def _cmake_targets_to_conan_components(self, targets_info, modules_info):
        # Fill in components based on VTK-targets.cmake and modules.json
        components = {}
        for name, target_info in targets_info.items():
            module_info = modules_info.get(name, {})
            component = {}
            if not target_info["is_interface"]:
                default_libname = f"vtk{name}" if not name.startswith("vtk") else name
                lib = module_info.get("lib_name", default_libname)
                component["libs"] = [lib + self._lib_suffix]
            for definition in target_info.get("compile_definitions", []):
                if definition.startswith("-D"):
                    definition = definition[2:]
                if "defines" not in component:
                    component["defines"] = []
                component["defines"].append(definition)
            requires, system_libs, frameworks = self._transform_link_libraries(target_info.get("link_libraries", []))
            requires += module_info.get("deps", [])
            requires = self._remove_duplicates(requires)
            if name in requires:
                # Only VTK::pugixml has this issue as of v9.3.1
                self.output.warning(f"CMake target VTK::{name} has a circular dependency on itself")
                requires.remove(name)
            if "vtkbuild" in requires:
                requires.remove("vtkbuild")
            if requires:
                component["requires"] = requires
            if system_libs:
                component["system_libs"] = self._remove_duplicates(system_libs)
            if frameworks:
                component["frameworks"] = self._remove_duplicates(frameworks)
            if module_info.get("implementable", False):
                component["implementable"] = True
            implements = module_info.get("implements", [])
            if implements:
                component["implements"] = implements
            components[name] = component
        return components

    @property
    def _components_json(self):
        return os.path.join(self.package_folder, "share", "conan", self.name, "conan_components.json")

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # VTK installs the licenses under the share/licenses/VTK directory, move it
        rename(self, os.path.join(self.package_folder, "share", "licenses", "VTK"),
               os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "share"))

        # Parse the VTK-targets.cmake file to generate Conan components
        targets_config = os.path.join(self.package_folder, "lib", "cmake", "vtk", "VTK-targets.cmake")
        cmake_target_props = self._parse_cmake_targets(targets_config)
        # Need to parse modules.json as well because private deps are missing from VTK-targets.cmake
        modules_json = os.path.join(self.build_folder, "modules.json")
        modules_info = self._get_info_from_modules_json(modules_json)
        # Generate components info for package_info()
        components = self._cmake_targets_to_conan_components(cmake_target_props, modules_info)
        save(self, self._components_json, json.dumps(components, indent=2))

        # Write autoinit headers
        self._generate_autoinits(modules_info)

        # create a cmake module with our special variables
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        cmake_module_path = os.path.join(self.package_folder, "lib", "cmake", "vtk", "conan-official-vtk-variables.cmake")
        save(self, cmake_module_path, textwrap.dedent("""\
            set(VTK_ENABLE_KITS FALSE)

            # Conan's VTK component targets propagate the generated autoinit definitions
            # and headers. Keep the upstream consumer API available; there is no remaining
            # target-local work for this function to perform.
            if(NOT COMMAND vtk_module_autoinit)
                function(vtk_module_autoinit)
                endfunction()
            endif()
        """))

    def _generate_autoinits(self, modules_info):
        ### VTK AUTOINIT ###
        # VTK has a special factory registration system, and modules that implement others have to be registered.
        # This mechanism was encoded into VTK's cmake autoinit system, which we (probably) can't use in a conan context.
        # So, we will implement the required autoinit registration things here.
        #
        # This recipe will ultimately generate special header files that contain lines like:
        #   #define vtkRenderingCore_AUTOINIT 2(vtkRenderingFreeType, vtkInteractionStyle)
        #       (this module is implemented)              (by these modules)
        #            IMPLEMENTABLE         by                 IMPLEMENTS
        #
        # There is one header per implementable module, and each user of an implementing-module must
        # have a special #define that tells the VTK system where this header is.  The header will be
        # included into the compilation and the autoinit system will register the implementing-module.
        #
        # But the trick is the library consumer will only declare they want to use an implementing module
        # (eg vtkRenderingOpenGL2) but will not use that module directly.
        # Instead, they will only use vtkRenderingCore and expect the OpenGL2 module to be magically built
        # by the core factory.  OpenGL2 module has to register with the Core module, without the library
        # consumer specifically calling the registration.
        #
        # VTK's cmake seems to generate headers for different combinations of components,
        #   so they need to create a unique autoinit file when a downstream consumer calls cmake function
        #   vtk_module_autoinit(TARGETS <target>... MODULES <module>...), so each target must know ALL
        #   of the vtk modules they will use (at cmake-time), and a unique header will be made for that combination.
        #  That header will be #included via a clever define for that target.
        #
        # This won't work in our case, and that would only work for cmake consumers.
        #
        # So I'm going to try a different approach:
        #  * define a header for all possible combinations of implementer-modules for an implementable-module.
        #  * use a define for each of the implementer-modules.  If a target is using that implementer-module,
        #     it will activate the autoinit for that module thanks to the #define flag
        #
        # Also note we have to be clever with the ordering of the combinations, as we only want to pick ONE of the combos.
        #
        # The max number of implementer combinations as of v9.3.1 is 2^7 - 1 = 127 for RenderingCore, which is tolerable.
        #
        # Example of an autoinit file with two implementers:
        ##  #if 0
        ##
        ##  #elif defined(VTK_CONAN_WANT_AUTOINIT_vtkRenderingOpenGL2) && defined(VTK_CONAN_WANT_AUTOINIT_vtkInteractionStyle)
        ##  #  define vtkRenderingCore_AUTOINIT 2(vtkRenderingOpenGL2,vtkInteractionStyle)
        ##
        ##  #elif defined(VTK_CONAN_WANT_AUTOINIT_vtkRenderingOpenGL2)
        ##  #  define vtkRenderingCore_AUTOINIT 1(vtkRenderingOpenGL2)
        ##
        ##  #elif defined(VTK_CONAN_WANT_AUTOINIT_vtkInteractionStyle)
        ##  #  define vtkRenderingCore_AUTOINIT 1(vtkInteractionStyle)
        ##
        ##  #endif

        # Gather all implementers for each implementable module
        autoinits = {mod: set() for mod, info in modules_info.items() if info["implementable"]}
        for module_name, module_info in modules_info.items():
            for implementable in module_info["implements"]:
                autoinits[implementable].add(module_name)
        # Write those special autoinit header files
        for implementable, all_implementers in autoinits.items():
            self.output.info(f"Generating autoinit headers for {implementable} with ({', '.join(all_implementers)}) implementers")
            all_implementers = [f"vtk{impl}" for impl in sorted(all_implementers)]
            content = "#if 0\n\n"
            for L in range(len(all_implementers), 0, -1):
                for combination in itertools.combinations(all_implementers, L):
                    content += f"#elif {' && '.join(f'defined(VTK_CONAN_WANT_AUTOINIT_{comp})' for comp in combination)}\n"
                    content += f"#  define vtk{implementable}_AUTOINIT {L}({','.join(combination)})\n\n"
            content += "#endif\n"
            autoinit_file = os.path.join(self.package_folder, "include", "vtk", "vtk-conan", f"vtk_autoinit_vtk{implementable}.h")
            save(self, autoinit_file, content)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "vtk")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["VTK"])
        version = Version(self.version)
        self.cpp_info.set_property("cmake_extra_variables", {
            "VTK_VERSION": str(version),
            "VTK_MAJOR_VERSION": int(str(version.major)),
            "VTK_MINOR_VERSION": int(str(version.minor)),
            "VTK_BUILD_VERSION": int(str(version.patch)),
        })

        cmake_modules_dir = os.path.join("lib", "cmake", "vtk")
        cmake_module_path = os.path.join(cmake_modules_dir, "conan-official-vtk-variables.cmake")
        self.cpp_info.builddirs = [cmake_modules_dir]
        self.cpp_info.set_property("cmake_build_modules", [cmake_module_path])

        # Define components based on the .json file generated in package()
        components = json.loads(load(self, self._components_json))
        for name, info in components.items():
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", f"VTK::{name}")
            component.includedirs = [os.path.join("include", "vtk")]
            component.libs = info.get("libs", [])
            component.defines = info.get("defines", [])
            component.requires = info.get("requires", [])
            component.system_libs = info.get("system_libs", [])
            component.frameworks = info.get("frameworks", [])
            # Add any required autoinit definitions for this component
            for implementable in info.get("implements", []):
                component.defines.append(f'vtk{implementable}_AUTOINIT_INCLUDE="vtk-conan/vtk_autoinit_vtk{implementable}.h"')
                component.defines.append(f"VTK_CONAN_WANT_AUTOINIT_vtk{name}")

        # Add some missing private dependencies
        missing_reqs = {
            "pugixml": ["pugixml::pugixml"],
            "CommonArchive": ["libarchive::libarchive"],
            "DomainsMicroscopy": ["openslide::openslide"],
            "GeovisGDAL": ["gdal::gdal"],
            "GUISupportQt": ["qt::qtOpenGL", "qt::qtWidgets", "qt::qtOpenGLWidgets"],
            "GUISupportQtQuick": ["qt::qtGui", "qt::qtOpenGL", "qt::qtQuick", "qt::qtQml"],
            "GUISupportQtSQL": ["qt::qtWidgets", "qt::qtSql"],
            "InfovisBoost": ["boost::headers", "boost::serialization"],
            "InfovisBoostGraphAlgorithms": ["boost::headers"],
            "IOAlembic": ["alembic::alembic"],
            "IOCatalystConduit": ["catalyst::catalyst"],
            "IOFFMPEG": ["ffmpeg::avformat", "ffmpeg::avcodec", "ffmpeg::avutil", "ffmpeg::swscale", "ffmpeg::swresample"],
            "IOGDAL": ["gdal::gdal"],
            "IOIFC": ["ifcopenshell::IfcParse", "ifcopenshell::IfcGeom"],
            "IOLAS": ["liblas::liblas", "boost::program_options", "boost::thread", "boost::iostreams", "boost::filesystem"],
            "IOMySQL": ["mariadb-connector-c::mariadb-connector-c"] if self.options.with_mysql == "mariadb-connector-c" else ["libmysqlclient::libmysqlclient"],
            "IOOCCT": ["opencascade::occt_tkstep", "opencascade::occt_tkiges", "opencascade::occt_tkmesh", "opencascade::occt_tkxdestep", "opencascade::occt_tkxdeiges"],
            "IOODBC": ["odbc::odbc"],
            "IOOpenVDB": ["openvdb::openvdb"],
            "IOPDAL": ["pdal::pdal"],
            "IOPostgreSQL": ["libpq::libpq"],
            "IOUSD": ["openusd::openusd"],
            "RenderingFreeTypeFontConfig": ["fontconfig::fontconfig"],
            "RenderingOpenVR": ["openvr::openvr"],
            "RenderingOpenXR": ["openxr::openxr"],
            "RenderingQt": ["qt::qtWidgets"],
            "RenderingVR": ["zeromq::zeromq"],
            "xdmf3": ["boost::headers"],
            "ViewsQt": ["qt::qtWidgets"],
        }
        for component, reqs in missing_reqs.items():
            if component in components:
                self.cpp_info.components[component].requires.extend(reqs)
        if self.options.smp_enable_tbb:
            self.cpp_info.components["CommonCore"].requires.append("onetbb::libtbb")
        if self.options.smp_enable_openmp:
            self.cpp_info.components["CommonCore"].requires.append("openmp::openmp")
        if self.options.with_memkind:
            self.cpp_info.components["CommonCore"].requires.append("memkind::memkind")
        if "RenderingOpenGL2" in components:
            if self.options.get_safe("with_x11"):
                self.cpp_info.components["RenderingOpenGL2"].requires.extend(["xorg::x11", "xorg::xcursor"])
            if self.options.get_safe("with_wayland"):
                self.cpp_info.components["RenderingOpenGL2"].requires.extend([
                    "wayland::wayland-client",
                    "wayland::wayland-egl",
                ])
            if self.options.get_safe("with_cocoa"):
                self.cpp_info.components["RenderingOpenGL2"].frameworks.append("Cocoa")
        if "RenderingUI" in components:
            if self.options.get_safe("with_x11"):
                self.cpp_info.components["RenderingUI"].requires.append("xorg::x11")
            if self.options.get_safe("with_wayland") and not self.options.get_safe("with_x11"):
                self.cpp_info.components["RenderingUI"].requires.extend([
                    "wayland::wayland-client",
                    "wayland::wayland-cursor",
                    "xkbcommon::libxkbcommon",
                ])
            if self.options.get_safe("with_cocoa"):
                self.cpp_info.components["RenderingUI"].frameworks.append("Cocoa")

        if self.options.want_all_modules:
            # Add a "poison" component to prohibit the use of the "vtk::vtk" Conan target.
            # This matches the project's behavior of not providing an aggregate VTK::VTK CMake target.
            msg = "_avoid_overlinking_against_the_whole_vtk_library_"
            self.cpp_info.components[msg].system_libs = [msg]
            self.cpp_info.set_property("cmake_target_name", msg)
            self.cpp_info.set_property("pkg_config_name", msg)

        for component_name, component in self.cpp_info.components.items():
            self.output.info(f"COMPONENT: {component_name}")
            if component.libs:
                self.output.info(f" - libs: {component.libs}")
            if component.defines:
                self.output.info(f" - defines: {component.defines}")
            if component.requires:
                self.output.info(f" - requires: {component.requires}")
            if component.system_libs:
                self.output.info(f" - system_libs: {component.system_libs}")
            if component.frameworks:
                self.output.info(f" - frameworks: {component.frameworks}")
