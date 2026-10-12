import os

from conan import ConanFile
from conan.tools.build import build_jobs, cross_building
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class EmSDKConan(ConanFile):
    name = "emsdk"
    description = "Emscripten SDK. Emscripten is an Open Source LLVM to JavaScript compiler"
    homepage = "https://github.com/kripken/emscripten"
    topics = ("emsdk", "emscripten", "sdk")
    license = "MIT"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @property
    def _relative_paths(self):
        return ["bin", os.path.join("bin", "upstream", "emscripten")]

    @property
    def _paths(self):
        return [os.path.join(self.package_folder, path) for path in self._relative_paths]

    @property
    def _emsdk(self):
        return os.path.join(self.package_folder, "bin")

    @property
    def _emscripten(self):
        return os.path.join(self.package_folder, "bin", "upstream", "emscripten")

    @property
    def _em_config(self):
        return os.path.join(self.package_folder, "bin", ".emscripten")

    @property
    def _em_cache(self):
        return os.path.join(self.package_folder, "bin", ".emscripten_cache")

    def generate(self):
        env = Environment()
        env.prepend_path("PATH", self._paths)
        env.define_path("EMSDK", self._emsdk)
        env.define_path("EMSCRIPTEN", self._emscripten)
        env.define_path("EM_CONFIG", self._em_config)
        env.define_path("EM_CACHE", self._em_cache)
        env.define("EMCC_CORES", str(build_jobs(self)))
        env.define("EMSDK_NUM_CORES", str(build_jobs(self)))
        env.vars(self, scope="emsdk").save_script("emsdk_env_file")

    @staticmethod
    def _chmod_plus_x(filename):
        if os.name == "posix":
            os.chmod(filename, os.stat(filename).st_mode | 0o111)

    def build(self):
        with chdir(self, self.source_folder):
            emsdk = "emsdk.bat" if self.settings_build.os == "Windows" else "./emsdk"
            self._chmod_plus_x("emsdk")
            self.run(f"{emsdk} install {self.version}")
            self.run(f"{emsdk} activate {self.version}")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        emscripten = os.path.join(self.package_folder, "bin", "upstream", "emscripten")
        toolchain = os.path.join(emscripten, "cmake", "Modules", "Platform", "Emscripten.cmake")
        # FIXME: conan should add the root of conan package requirements to CMAKE_PREFIX_PATH (LIBRARY/INCLUDE -> ONLY; PROGRAM -> NEVER)
        # allow to find conan libraries
        replace_in_file(self, toolchain,
                              "set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)",
                              "set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)")
        replace_in_file(self, toolchain,
                              "set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)",
                              "set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)")
        replace_in_file(self, toolchain,
                              "set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)",
                              "set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)")
        if not cross_building(self):
            self.run("embuilder build MINIMAL", env=["conanemsdk", "conanrun"]) # force cache population
            # the line below forces emscripten to accept the cache as-is, even after re-location
            # https://github.com/emscripten-core/emscripten/issues/15053#issuecomment-920950710
            os.remove(os.path.join(self._em_cache, "sanity.txt"))

    def _define_tool_var(self, value):
        suffix = ".exe" if self.settings.os == "Windows" and Version(self.version) >= "6" else \
                 ".bat" if self.settings.os == "Windows" else ""
        path = os.path.join(self._emscripten, f"{value}{suffix}")
        self._chmod_plus_x(path)
        return path

    @property
    def _node_bindirs(self):
        node_root = os.path.join(self.package_folder, "bin", "node")
        if not os.path.isdir(node_root):
            return []
        return [os.path.join("bin", "node", version, "bin")
                for version in sorted(os.listdir(node_root))]

    def package_info(self):
        self.cpp_info.bindirs = self._relative_paths + self._node_bindirs
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        # If we are not building for Emscripten, probably we don't want to inject following environment variables,
        #   but it might be legit use cases... until we find them, let's be conservative.
        if self.context != "build":
            return

        if self.settings_target.os != "Emscripten":
            self.output.warning(f"You've added {self.ref} as a build requirement, while os={self.settings_target.os} != Emscripten")
            return

        toolchain = os.path.join(self.package_folder, "bin", "upstream", "emscripten", "cmake", "Modules", "Platform", "Emscripten.cmake")
        self.conf_info.prepend("tools.cmake.cmaketoolchain:user_toolchain", toolchain)

        self.buildenv_info.define_path("EMSDK", self._emsdk)
        self.buildenv_info.define_path("EMSCRIPTEN", self._emscripten)
        self.buildenv_info.define_path("EM_CONFIG", self._em_config)
        self.buildenv_info.define_path("EM_CACHE",  self._em_cache)

        compiler_executables = {
            "c": self._define_tool_var("emcc"),
            "cpp": self._define_tool_var("em++"),
        }
        self.conf_info.update("tools.build:compiler_executables", compiler_executables)
        self.buildenv_info.define_path("CC", compiler_executables["c"])
        self.buildenv_info.define_path("CXX", compiler_executables["cpp"])
        self.buildenv_info.define_path("AR", self._define_tool_var("emar"))
        self.buildenv_info.define_path("NM", self._define_tool_var("emnm"))
        self.buildenv_info.define_path("RANLIB", self._define_tool_var("emranlib"))
        self.buildenv_info.define_path("STRIP", self._define_tool_var("emstrip"))

        self.cpp_info.builddirs = [
            "bin/releases/src",
            "bin/upstream/emscripten/cmake/Modules",
            "bin/upstream/emscripten/cmake/Modules/Platform",
            "bin/upstream/emscripten/system/lib/libunwind/cmake/Modules",
            "bin/upstream/emscripten/system/lib/libunwind/cmake",
            "bin/upstream/emscripten/tests/cmake/target_library",
            "bin/upstream/lib/cmake/llvm",
        ]
