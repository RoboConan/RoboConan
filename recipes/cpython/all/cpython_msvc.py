import fnmatch
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import can_run
from conan.tools.files import *
from conan.tools.microsoft import *
from conan.tools.scm import Version


class CPythonMSVC(ConanFile):
    @property
    def _msvc_archs(self):
        return {
            "x86": "Win32",
            "x86_64": "x64",
            "armv7": "ARM",
            "armv8_32": "ARM",
            "armv8": "ARM64",
        }

    def _msvc_build_requirements(self):
        pass

    def _msvc_validate(self):
        # FIXME: should probably throw when cross building
        # TODO: pgo support for Visual Studio, before building the final `build_type`:
        # 1. build the MSVC PGInstrument build_type,
        # 2. run the instrumented binaries, (PGInstrument should have created a `python.bat` file in the PCbuild folder)
        # 3. build the MSVC PGUpdate build_type
        if str(self.settings.arch) not in self._msvc_archs:
            raise ConanInvalidConfiguration("Visual Studio does not support this architecture")
        if is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration("MT(d) runtime is not supported when building a shared cpython library")
        if self.settings.build_type == "Debug" and "d" not in msvc_runtime_flag(self):
            raise ConanInvalidConfiguration(
                "Building debug cpython requires a debug runtime (Debug cpython requires _CrtReportMode"
                " symbol, which only debug runtimes define)"
            )
        if self.options.get_safe("with_bz2") == False:
            raise ConanInvalidConfiguration("with_bz2 option cannot be disabled when building with MSVC")
        if self.options.get_safe("with_zstd") == False:
            raise ConanInvalidConfiguration("with_zstd option cannot be disabled when building with MSVC")

    def _msvc_generate(self):
        tc = MSBuildToolchain(self)
        tc.properties["IncludeExternals"] = "true"
        tc.properties["DisableGil"] = "true" if self.options.get_safe("freethreaded") else "false"
        if Version(self.version) >= "3.15":
            tc.properties["UsePymallocHugepages"] = "true" if self.options.pymalloc_hugepages else "false"
        tc.generate()
        deps = MSBuildDeps(self)
        deps.generate()

    ## PATCH

    def _replace_in_vcxproj(self, path, search, replace, strict=True):
        return replace_in_file(self, f"{path}.vcxproj", search, replace, strict=strict)

    def _inject_conan_props_file(self, path, dep_name, condition=True):
        if condition:
            search = '<Import Project="python.props" />'
            inject = f'<Import Project="{self.generators_folder}/conan_{dep_name}.props" />'
            self._replace_in_vcxproj(path, search, search + inject)

    def _disable_vcxproj_element(self, path, elem_pattern):
        if "Condition" in elem_pattern:
            disabled_element, n = re.subn('Condition=".+?"', 'Condition="False"', elem_pattern)
            assert n == 1
        else:
            disabled_element = elem_pattern.replace('>', ' Condition="False">')
        self._replace_in_vcxproj(path, elem_pattern, disabled_element)

    def _remove_vcxproj_include_dir(self, path, include_pattern):
        if not include_pattern.endswith(";"):
            include_pattern += ";"
        self._regex_replace_in_file(f"{path}.vcxproj",
                                    f"<AdditionalIncludeDirectories[^>]*>([^<]*){re.escape(include_pattern)}",
                                    r"<AdditionalIncludeDirectories>\1")

    def _remove_vcxproj_dependency(self, path, dir_pattern):
        if not dir_pattern.endswith(";"):
            dir_pattern += ";"
        self._regex_replace_in_file(f"{path}.vcxproj",
                                    f"<AdditionalDependencies[^>]*>([^<]*){re.escape(dir_pattern)}",
                                    r"<AdditionalDependencies>\1")

    def _inject_vcxproj_element(self, path, elem_pattern, inject, prepend=False):
        self._replace_in_vcxproj(path, elem_pattern, inject + elem_pattern if prepend else elem_pattern + inject)

    def _regex_replace_in_file(self, filename, pattern, replacement, strict = True) -> None:
        content = load(self, filename)
        content, n = re.subn(pattern, replacement, content)
        if strict and n == 0:
            raise ConanException(f"Pattern '{pattern}' not found in '{filename}'")
        self.output.debug(f"Pattern '{pattern}' found {n} times in '{filename}'")
        save(self, filename, content)

    def _remove_vcxproj_source_files(self, path, glob_pattern):
        glob_regex = fnmatch.translate(glob_pattern)[4:-3].replace(".*", '[^"]*')
        pattern = fr'<(CLCompile|ClInclude|\w+) [^>]*Include="{glob_regex}"[^>]*?(/>|>[\s\S]*?</\1>)'
        self._regex_replace_in_file(f"{path}.vcxproj", pattern, "", re.DOTALL)

    def _patch_solution(self):
        self._regex_replace_in_file(
            "pcbuild.sln",
            r'(?m)(^Project\("[^"]+"\) = "python", "python\.vcxproj", "[^"]+"\r?\n)'
            r'\tProjectSection\(ProjectDependencies\) = postProject\r?\n'
            r'(?:\t\t[^\r\n]*\r?\n)+'
            r'\tEndProjectSection\r?\n',
            r'\1',
        )
        if Version(self.version, qualifier=True) >= "3.14":
            self._regex_replace_in_file(
                "pcbuild.sln",
                r'(?m)^Project\("[^"]+"\) = "zlib-ng", "zlib-ng\.vcxproj", "[^"]+"\r?\n'
                r'EndProject\r?\n',
                "",
            )

    def _patch_msvc(self):
        runtime_library = {
            "MT": "MultiThreaded",
            "MTd": "MultiThreadedDebug",
            "MD": "MultiThreadedDLL",
            "MDd": "MultiThreadedDebugDLL",
        }[msvc_runtime_flag(self)]
        self.output.info("Patching runtime")
        replace_in_file(self, "pyproject.props", "MultiThreadedDLL", runtime_library)
        replace_in_file(self, "pyproject.props", "MultiThreadedDebugDLL", runtime_library)

        # bz2
        self._remove_vcxproj_source_files("_bz2", "$(bz2Dir)*")

        # openssl
        if Version(self.version) < "3.12":
            self._remove_vcxproj_source_files("_ssl", r"$(opensslIncludeDir)\applink.c")

        # libffi
        if Version(self.version) < "3.11":
            # Don't add this define, it should be added conditionally by the libffi package
            # Instead, add this define to fix duplicate symbols (goes along with the ffi patches)
            # See https://github.com/python/cpython/commit/38f331d4656394ae0f425568e26790ace778e076#diff-6f6b7f83e2fb49775efdfa41b4aa4f8fadcf71f43c4f3bcf9f37743acafd3fdfR97
            self._replace_in_vcxproj("_ctypes", "FFI_BUILDING;", "USING_MALLOC_CLOSURE_DOT_C=1;")

        # mpdecimal
        # We need to remove all headers and all c files *except* the main module file, _decimal.c
        if Version(self.version) >= "3.13":
            self._remove_vcxproj_source_files("_decimal", r"..\Modules\_decimal\windows\*.h")
            self._remove_vcxproj_source_files("_decimal", r"$(mpdecimalDir)\libmpdec\*")
            self._remove_vcxproj_include_dir("_decimal", r"..\Modules\_decimal\windows;$(mpdecimalDir)\libmpdec")
        else:
            self._remove_vcxproj_source_files("_decimal", r"..\Modules\_decimal\*.h")
            self._remove_vcxproj_source_files("_decimal", r"..\Modules\_decimal\libmpdec\*")
            self._remove_vcxproj_include_dir("_decimal", r"..\Modules\_decimal\libmpdec")

        # sqlite3
        self._disable_vcxproj_element("_sqlite3", '<ProjectReference Include="sqlite3.vcxproj">')

        # lzma
        self._remove_vcxproj_dependency("_lzma", "$(OutDir)liblzma$(PyDebugExt).lib")
        self._disable_vcxproj_element("_lzma", '<ProjectReference Include="liblzma.vcxproj">')

        # expat
        self._remove_vcxproj_include_dir("pyexpat", "$(PySourcePath)Modules\expat")
        self._remove_vcxproj_include_dir("_elementtree", r"..\Modules\expat")
        # Let Conan handle XML_STATIC
        self._replace_in_vcxproj("pyexpat", "XML_STATIC;", "")
        self._replace_in_vcxproj("_elementtree", "XML_STATIC;", "")
        self._remove_vcxproj_source_files("pyexpat", r"..\Modules\expat\*")
        self._remove_vcxproj_source_files("_elementtree", r"..\Modules\expat\*")

        # zlib
        if Version(self.version, qualifier=True) >= "3.14":
            self._remove_vcxproj_dependency("pythoncore", "zlib-ng$(PyDebugExt).lib")
            self._remove_vcxproj_include_dir("pythoncore", "$(zlibNgDir);$(GeneratedZlibNgDir)")
            self._remove_vcxproj_source_files("pythoncore", "zlib-ng.vcxproj")
        else:
            self._remove_vcxproj_source_files("pythoncore", r"$(zlibDir)\*")

        # tcl/tk
        self._remove_vcxproj_include_dir("_tkinter", "$(tcltkDir)include")
        self._remove_vcxproj_dependency("_tkinter", "$(tcltkLib)")
        self._disable_vcxproj_element("_tkinter", "<PreprocessorDefinitions Condition=\"'$(BuildForRelease)' != 'true'\">Py_TCLTK_DIR")
        self._remove_vcxproj_source_files("_tkinter", r"$(tcltkdir)\*")

        if Version(self.version, qualifier=True) >= "3.14":
            self._remove_vcxproj_include_dir("_zstd", r"$(zstdDir)lib\;$(zstdDir)lib\common;$(zstdDir)lib\compress;$(zstdDir)lib\decompress;$(zstdDir)lib\dictBuilder;")
            self._remove_vcxproj_source_files("_zstd", r"$(zstdDir)*")

        # Inject Conan toolchain
        conantoolchain_props = os.path.join(self.generators_folder, MSBuildToolchain.filename)
        self._inject_vcxproj_element("pythoncore",
                                     '<Import Project="python.props" />',
                                     f'<Import Project="{conantoolchain_props}" />', prepend=True)

        # Don't import vendored libs
        self._replace_in_vcxproj("_ctypes", '<Import Project="libffi.props" />', "")
        self._replace_in_vcxproj("_hashlib", '<Import Project="openssl.props" />', "")
        self._replace_in_vcxproj("_ssl", '<Import Project="openssl.props" />', "")

        # Inject Conan deps
        self._inject_conan_props_file("_bz2", "bzip2", self.options.get_safe("with_bz2"))
        self._inject_conan_props_file("_elementtree", "expat")
        self._inject_conan_props_file("pyexpat", "expat")
        self._inject_conan_props_file("_hashlib", "openssl")
        self._inject_conan_props_file("_ssl", "openssl")
        self._inject_conan_props_file("_sqlite3", "sqlite3", self.options.get_safe("with_sqlite3"))
        self._inject_conan_props_file("_tkinter", "tk", self.options.get_safe("with_tkinter"))
        self._inject_conan_props_file("pythoncore", "zlib-ng")
        self._inject_conan_props_file("python", "zlib-ng")
        self._inject_conan_props_file("pythonw", "zlib-ng")
        self._inject_conan_props_file("_ctypes", "libffi")
        self._inject_conan_props_file("_decimal", "mpdecimal")
        self._inject_conan_props_file("_lzma", "xz_utils", self.options.get_safe("with_lzma"))
        self._inject_conan_props_file("_bsddb", "libdb", self.options.get_safe("with_bsddb"))
        self._inject_conan_props_file("_zstd", "zstd", self.options.get_safe("with_zstd"))

    def _msvc_patch_sources(self):
        with chdir(self, os.path.join(self.source_folder, "PCbuild")):
            self._patch_solution()
            self._patch_msvc()

    ## BUILD

    @property
    def _solution_projects(self):
        solution_path = os.path.join(self.source_folder, "PCbuild", "pcbuild.sln")
        projects = set(re.findall(r'"([^"]+)\.vcxproj"', open(solution_path).read()))

        def project_build(name):
            if os.path.basename(name) in self._msvc_discarded_projects:
                return False
            return "test" not in name

        projects = list(filter(project_build, projects))
        return projects

    @property
    def _msvc_discarded_projects(self):
        discarded = {
            "python_uwp",
            "pythonw_uwp",
            "_freeze_importlib",
            "sqlite3",
            "bdist_wininst",
            "liblzma",
            "openssl",
            "xxlimited",
        }
        if not self.options.with_bz2:
            discarded.add("bz2")
        if not self.options.with_sqlite3:
            discarded.add("_sqlite3")
        if not self.options.with_tkinter:
            discarded.add("_tkinter")
        if not self.options.with_lzma:
            discarded.add("_lzma")
        return discarded

    def _msvc_build(self):
        msbuild = MSBuild(self)
        msbuild.platform = self._msvc_archs[str(self.settings.arch)]

        projects = self._solution_projects
        self.output.info(f"Building {len(projects)} Visual Studio projects: {projects}")

        sln = os.path.join(self.source_folder, "PCbuild", "pcbuild.sln")
        # FIXME: Solution files do not pick up the toolset automatically.
        cmd = msbuild.command(sln, targets=projects)
        cmd += f" /p:PlatformToolset={msvs_toolset(self)}"
        cmd += f" /p:DisableGil={'true' if self.options.get_safe('freethreaded') else 'false'}"
        if Version(self.version) >= "3.15":
            cmd += f" /p:UsePymallocHugepages={'true' if self.options.pymalloc_hugepages else 'false'}"
        self.run(cmd)

    ## PACKAGE

    @property
    def _msvc_artifacts_path(self):
        build_subdir_lut = {
            "x86_64": "amd64",
            "x86": "win32",
            "armv7": "arm32",
            "armv8_32": "arm32",
            "armv8": "arm64",
        }
        build_subdir = build_subdir_lut[str(self.settings.arch)]
        if self.options.get_safe("freethreaded"):
            build_subdir += "t"
        return os.path.join(self.source_folder, "PCbuild", build_subdir)

    @property
    def _msvc_install_subprefix(self):
        return "bin"

    def _copy_essential_dlls(self):
        # Until MSVC builds support cross building, copy dll's of essential (shared) dependencies to python binary location.
        # These dll's are required when running the layout tool using the newly built python executable.
        dest_path = os.path.join(self.build_folder, self._msvc_artifacts_path)
        for bin_path in self.dependencies["libffi"].cpp_info.bindirs:
            copy(self, "*.dll", src=bin_path, dst=dest_path)
        for bin_path in self.dependencies["expat"].cpp_info.bindirs:
            copy(self, "*.dll", src=bin_path, dst=dest_path)
        for bin_path in self.dependencies["zlib-ng"].cpp_info.bindirs:
            copy(self, "*.dll", src=bin_path, dst=dest_path)
        for bin_path in self.dependencies["openssl"].cpp_info.bindirs:
            copy(self, "*.dll", src=bin_path, dst=dest_path)

    def _msvc_package_layout(self):
        install_prefix = os.path.join(self.package_folder, self._msvc_install_subprefix)
        mkdir(self, install_prefix)
        build_path = self._msvc_artifacts_path
        if can_run(self):
            self._copy_essential_dlls()
            infix = "_d" if self.settings.build_type == "Debug" else ""
            python_exe = os.path.join(build_path, f"python{infix}.exe")
        else:
            python_exe = "python"
        layout_args = [
            os.path.join(self.source_folder, "PC", "layout", "main.py"),
            "-v",
            "--source", self.source_folder,
            "--build", build_path,
            "--copy", install_prefix,
            "--precompile",
            "--include-pip",
            "--include-venv",
            "--include-dev",
        ]
        if self.options.with_tkinter:
            layout_args.append("--include-tcltk")
        if self.settings.build_type == "Debug":
            layout_args.append("-d")
        if Version(self.version) >= "3.12":
            layout_args.append("--include-stable")
        if Version(self.version) >= "3.13":
            # add aliases for python.exe, python3.exe, python3.x.exe
            layout_args.extend([
                "--include-alias",
                "--include-alias3",
                "--include-alias3x",
            ])
            if self.options.freethreaded:
                layout_args.append("--include-freethreaded")
        python_args = " ".join(f'"{a}"' for a in layout_args)
        self.run(f"{python_exe} {python_args}")

        rmdir(self, os.path.join(self.package_folder, "bin", "tcl"))

        rm(self, "LICENSE.txt", install_prefix)
        for file in os.listdir(os.path.join(install_prefix, "libs")):
            if not re.match("python.*", file):
                os.unlink(os.path.join(install_prefix, "libs", file))

    def _msvc_package(self):
        self._msvc_package_layout()
        rm(self, "vcruntime*", os.path.join(self.package_folder, "bin"), recursive=True)
