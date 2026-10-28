import os
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.gnu import AutotoolsDeps
from conan.tools.microsoft import is_msvc, VCVars
from conan.tools.scm import Version


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # run=True for the stdlib module tests to work even for shared=False.
        # Without it, Conan does not add libpython.so required by the interpreter to LD_LIBRARY_PATH.
        self.requires(self.tested_reference_str, run=can_run(self))

    def build_requirements(self):
        # These tests can break pip-installed CMake, so add it as a tool_requires.
        # CMake 4.4 teaches Python3_add_library() to target abi3t for
        # free-threaded Python 3.15 when USE_SABI is requested.
        self.tool_requires("cmake/[^4.4]")
        self.tool_requires("cpython/<host_version>")

    def layout(self):
        cmake_layout(self)

    def _cpython_option(self, name, default=False):
        return self.dependencies["cpython"].options.get_safe(name, default)

    @property
    def _py_version(self):
        return Version(str(self.dependencies["cpython"].ref.version).split("-")[0])

    @property
    def _test_setuptools(self):
        # TODO Should we still try to test this?
        # https://github.com/python/cpython/pull/101039
        return self._py_version < "3.12"

    @property
    def _supports_modules(self):
        # Modules cannot be linked against a static libpython
        return self._cpython_option("shared", True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_MODULE"] = self._supports_modules
        python = self.dependencies.build["cpython"].conf_info.get(
            "user.cpython:python", check_type=str
        ).replace("\\", "/")
        tc.cache_variables["Python3_EXECUTABLE"] = python
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        if self._test_setuptools:
            if is_msvc(self):
                VCVars(self).generate()
            # Just for the setuptools build
            AutotoolsDeps(self).generate(scope="build")

    def build(self):
        buffer = StringIO()
        self.run('python -c "import sys; print(\'.\'.join(str(s) for s in sys.version_info[:3]))"', buffer)
        self.output.info(buffer.getvalue())
        version_detected = buffer.getvalue().splitlines()[-1].strip()
        if self._py_version != version_detected:
            raise ConanException(f"python reported wrong version. Expected {self._py_version}. Got {version_detected}.")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if self._test_setuptools:
            setup_args = [
                os.path.join(self.source_folder, "setup.py"),
                "build",
                "--build-base", self.build_folder,
                "--build-platlib", os.path.join(self.build_folder, "lib_setuptools"),
                # Bandaid fix: setuptools places temporary files in a subdirectory of the build folder where the
                # entirety of the absolute path up to this folder is appended (with seemingly no way to stop this),
                # essentially doubling the path length. This may run into Windows max path lengths, so we give ourselves
                # a little bit of wiggle room by making this directory name as short as possible. One of the directory
                # names goes from (for example) "temp.win-amd64-3.10-pydebug" to "t", saving us roughly 25 characters.
                "--build-temp", "t",
            ]
            if self.settings.build_type == "Debug":
                setup_args.append("--debug")
            args = " ".join(f'"{a}"' for a in setup_args)

            env = Environment()
            env.define("DISTUTILS_USE_SDK", "1")
            env.define("MSSdk", "1")
            with env.vars(self).apply():
                self.run(f"python {args}")

    def _test_module(self, module, should_work):
        retcode = self.run(f'python "{self.source_folder}/test_package.py" -b "{self.build_folder}" -t {module}',
                           ignore_errors=True, env="conanrun")
        if retcode == 0:
            if not should_work:
                raise ConanException(f"Module '{module}' works, but should not have")
            self.output.info("Module worked as expected")
        else:
            if should_work:
                raise ConanException(f"Module '{module}' does not work, but should have")
            self.output.info("Module failed as expected")

    def test(self):
        if can_run(self):
            if not is_msvc(self):
                self.run("python3-config --prefix", env="conanrun")

            code = (f"import sys; assert '.'.join(map(str, sys.version_info[:3])) == "
                    f"'{self._py_version}', sys.version")
            if self._py_version >= "3.13":
                gil_enabled = not self._cpython_option("freethreaded")
                code += f"; assert sys._is_gil_enabled() is {gil_enabled}"
            self.run(f'python -c "{code}"', env="conanrun")

            self._test_module("gdbm", self._cpython_option("with_gdbm"))
            self._test_module("bz2", self._cpython_option("with_bz2"))
            self._test_module("lzma", self._cpython_option("with_lzma"))
            self._test_module("zstd", self._cpython_option("with_zstd"))
            self._test_module("tkinter", self._cpython_option("with_tkinter"))
            env = Environment()
            env.define("TERM", "ansi")
            with env.vars(self).apply():
                self._test_module("curses", self._cpython_option("with_curses"))
            self._test_module("expat", True)
            self._test_module("sqlite3", self._cpython_option("with_sqlite3"))
            self._test_module("decimal", True)
            self._test_module("ctypes", True)
            self._test_module("readline", self._cpython_option("with_readline"))
            env = Environment()
            if self.settings.os != "Windows":
                env.define_path("OPENSSL_CONF", os.path.join(os.sep, "dev", "null"))
            with env.vars(self).apply():
                self._test_module("ssl", True)

            if self._supports_modules:
                self.output.info("Testing module (spam) using cmake built module")
                env = Environment()
                env.define_path("PYTHONPATH", os.path.join(self.build_folder, self.cpp.build.libdirs[0]))
                with env.vars(self).apply():
                    self._test_module("spam", True)
                    if self._py_version >= "3.15":
                        self._test_module("spam_sabi", True)

                if self._test_setuptools:
                    self.output.info("Testing module (spam) using setup.py built module")
                    env.define_path("PYTHONPATH", os.path.join(self.build_folder, "lib_setuptools"))
                    with env.vars(self).apply():
                        self._test_module("spam", True)

            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
