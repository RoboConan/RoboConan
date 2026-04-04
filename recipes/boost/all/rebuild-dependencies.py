#!/usr/bin/env python3

import argparse
import dataclasses
import logging
import platform
import pprint
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Union

import yaml
from conan.tools.files import chdir
from conan.tools.scm import Version

script_dir = Path(__file__).parent.resolve()

log = logging.Logger("boost-dependency-builder")
log.parent = logging.root
log.setLevel(logging.WARNING)


BOOST_GIT_URL = "https://github.com/boostorg/boost.git"

# When adding (or removing) an option, also add this option to the list in
# `conanfile.py` and re-run this script.
CONFIGURE_OPTIONS = (
    "atomic",
    "charconv",
    "chrono",
    "cobalt",
    "container",
    "context",
    "contract",
    "coroutine",
    "date_time",
    "exception",
    "fiber",
    "filesystem",
    "graph",
    "graph_parallel",
    "iostreams",
    "json",
    "locale",
    "log",
    "math",
    "mpi",
    "nowide",
    "process",
    "program_options",
    "python",
    "random",
    "regex",
    "serialization",
    "stacktrace",
    "test",
    "thread",
    "timer",
    "type_erasure",
    "url",
    "wave",
)


CONAN_REQUIREMENTS = (
    "backtrace",
    "bzip2",
    "iconv",
    "icu",
    "lzma",
    "python",
    "zlib",
    "zstd",
)


LINUX_SYSTEM_LIBS = (
    "dl",
    "m",
    "rt",
    "pthread",
)


WINDOWS_SYSTEM_LIBS = (
    "bcrypt",
    "coredll",
    "dbgeng",
)


@dataclasses.dataclass
class BoostDependenciesExport:
    version: str
    configure_options: List[str]
    dependencies: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    libs: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    requirements: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    static_only: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class BoostDependencies:
    buildables: List[str]
    export: BoostDependenciesExport


class BoostDependencyBuilder:
    def __init__(self, boost_version: str, boostdep_version: str, tmppath: Union[str, Path], git_url: str):
        self.boost_version = boost_version
        self.boostdep_version = boostdep_version
        self.git_url = git_url
        self.tmppath = Path(tmppath)
        self._boostdep = None

    @property
    def boost_path(self) -> Path:
        return self.tmppath / "boost"

    def do_git_clone(self) -> None:
        subprocess.check_call([
            "git", "clone",
            "--depth", "1",
            "--branch", f"boost-{self.boost_version}",
            "--",
            self.git_url,
            str(self.boost_path),
        ])
        with chdir(self, self.boost_path):
            subprocess.check_call(["git", "submodule", "update", "--init", "--depth", "1", "-j", "10"])

    def do_install_boostdep(self):
        self.boost_path.mkdir(parents=True, exist_ok=True)
        with chdir(self, self.boost_path):
            print(f"Installing boostdep/{self.boostdep_version}")
            subprocess.check_output([
                "conan", "install",
                "--tool-requires", f"boostdep/{self.boostdep_version}",
                "--deployer=direct_deploy",
                "--build=missing",
            ])
            suffix = ".exe" if platform.system() == "Windows" else ""
            self._boostdep = self.boost_path / "direct_deploy" / "boostdep" / "bin" / f"boostdep{suffix}"

    @staticmethod
    def _grep_libs(regex, text):
        res = set()
        for m in re.finditer(regex, text, flags=re.MULTILINE):
            if any(ign in m.group(1) for ign in ["#", '"']):
                continue
            library = m.group(2).lower()
            if any(ign in library for ign in ["boost", "<", ">"]):
                continue
            res.add(library)
        return sorted(res)

    def _grep_requirements(self, component: str) -> List[str]:
        jam = self.boost_path / "libs" / component / "build" / "Jamfile.v2"
        if not jam.is_file():
            jam = self.boost_path / "libs" / component / "build" / "Jamfile"
        if not jam.is_file():
            log.warning("Can't find Jamfile for %s. Unable to determine dependencies.", component)
            return []
        contents = jam.open().read()

        using = self._grep_libs("\n(.*)using\\s+([^ ;:]+)\\s*", contents)
        libs = self._grep_libs("\n(.*)\\s(?:searched-)?lib\\s+([^ \t\n;:]+)", contents)

        requirements = using + libs
        return requirements

    @staticmethod
    def _sort_requirements(requirements: List[str]) -> Tuple[List[str], Dict[str, List[str]], List[str]]:
        conan_requirements = set()
        system_libs = {}
        unknown_libs = set()

        for req in requirements:
            if req in LINUX_SYSTEM_LIBS:
                system_libs.setdefault("linux", []).append(req)
                continue
            if req in WINDOWS_SYSTEM_LIBS:
                system_libs.setdefault("windows", []).append(req)
                continue
            added = False
            for conan_req in CONAN_REQUIREMENTS:
                if conan_req in req:
                    conan_requirements.add(conan_req)
                    added = True
            if added:
                continue
            unknown_libs.add(req)
        return sorted(conan_requirements), system_libs, sorted(unknown_libs)

    def do_boostdep_collect(self) -> BoostDependencies:
        with chdir(self, self.boost_path):
            buildables = subprocess.check_output([self._boostdep, "--list-buildable"], text=True)
            buildables = buildables.splitlines()
            log.debug("`boostdep --list--buildable` returned these buildables: %s", buildables)

            # modules = subprocess.check_output([self._boostdep_path, "--list-modules"])
            # modules = modules.decode().splitlines()

            dependency_tree = {}
            buildable_dependencies = subprocess.check_output([self._boostdep, "--list-buildable-dependencies"], text=True)
            log.debug("boostdep --list-buildable-dependencies returns: %s", buildable_dependencies)
            for line in buildable_dependencies.splitlines():
                if re.match(r"^\s*#.*", line):
                    continue
                match = re.match(r"(\S+)\s*=\s*([^;]+)\s*;\s*", line)
                if not match:
                    continue
                master = match.group(1)
                dependencies = re.split(r"\s+", match.group(2).strip())
                dependency_tree[master] = dependencies

            log.debug("Using `boostdep --track-sources`, the following dependency tree was calculated:")
            log.debug(pprint.pformat(dependency_tree))

        filtered_dependency_tree = {k: [d for d in v if d in buildables] for k, v in dependency_tree.items() if k in buildables}

        configure_options = []
        for conf_option in CONFIGURE_OPTIONS:
            if conf_option in filtered_dependency_tree:
                configure_options.append(conf_option)
            else:
                log.warning("option %s not available in %s", conf_option, self.boost_version)

        log.debug("Following config_options remain: %s", configure_options)

        requirements = {}
        for conf_option in configure_options:
            reqs = self._grep_requirements(conf_option)
            conan_requirements, system_libs, unknown_libs = self._sort_requirements(reqs)
            if system_libs:
                log.warning("Module '%s' (%s) has system libraries: %s", conf_option, self.boost_version, system_libs)
            if unknown_libs:
                log.warning("Module '%s' (%s) has unknown libs: %s", conf_option, self.boost_version, unknown_libs)
            if conan_requirements:
                requirements[conf_option] = conan_requirements

        boost_dependencies = BoostDependencies(
            export=BoostDependenciesExport(
                version=self.boost_version,
                configure_options=configure_options,
                dependencies=filtered_dependency_tree,
                requirements=requirements,
                static_only=[],
            ),
            buildables=buildables,
        )

        return boost_dependencies

    @staticmethod
    def detect_cycles(tree: Dict[str, List[str]]) -> Dict[str, List[str]]:
        tree = {k: v[:] for k, v in tree.items()}
        while tree:
            nodeps = set(k for k, v in tree.items() if not v)
            if not nodeps:
                return tree
            tree = {k: [d for d in v if d not in nodeps] for k, v in tree.items() if k not in nodeps}
        return {}

    def _fix_dependencies(self, deptree: Dict[str, List[str]]) -> Dict[str, List[str]]:
        try:
            # python does not depend on graph
            deptree["python"].remove("graph")
        except (KeyError, ValueError):
            pass

        try:
            # graph does not depend on graph_parallel
            deptree["graph"].remove("graph_parallel")
        except (KeyError, ValueError):
            pass

        try:
            # mpi does not depend on python
            deptree["mpi"].remove("python")
        except (KeyError, ValueError):
            pass

        if "mpi_python" in deptree and "python" not in deptree["mpi_python"]:
            deptree["mpi_python"].append("python")

        # Break random/math dependency cycle
        try:
            deptree["math"].remove("random")
        except ValueError:
            pass

        remaining_tree = self.detect_cycles(deptree)
        if remaining_tree:
            raise Exception(f"Dependency cycle detected. Remaining tree: {remaining_tree}")
        return deptree

    @staticmethod
    def _boostify_library(lib: str) -> str:
        return f"boost_{lib}"

    def do_create_libraries(self, boost_dependencies: BoostDependencies):
        libraries = {}
        module_provides_extra = {}

        #  Look for the names of libraries in Jam build files
        for buildable in boost_dependencies.buildables:
            construct_jam = lambda jam_ext : self.boost_path / "libs" / buildable / "build" / f"Jamfile{jam_ext}"
            try:
                buildable_jam = next(construct_jam(jam_ext) for jam_ext in ("", ".v2") if construct_jam(jam_ext).is_file())
            except StopIteration:
                raise Exception(f"Cannot find jam build file for {buildable}")
            jam_text = buildable_jam.read_text()
            buildable_libs = re.findall(r"[ \n](boost-)?lib (\w+)[ \n]", jam_text)
            buildable_libs = set(f"boost_{lib}" if lib_prefix else lib for lib_prefix, lib in buildable_libs)
            buildable_libs = set(l[len("boost_"):] for l in buildable_libs if l.startswith("boost_"))

            if not buildable_libs:
                # Some boost releases support multiple python versions
                if buildable == "python":
                    buildable_libs.add("python")
            if not buildable_libs:
                raise Exception(f"Cannot find any library for buildable {buildable}")

            if buildable in buildable_libs:
                libraries[buildable] = [f"boost_{buildable}"]
                buildable_libs.remove(buildable)
            else:
                libraries[buildable] = []
            module_provides_extra[buildable] = buildable_libs
            for buildable_dep in buildable_libs:
                boost_dependencies.export.dependencies[buildable_dep] = [buildable]
                libraries[buildable_dep] = [f"boost_{buildable_dep}"]

        # Boost.Test: unit_test_framework depends on all libraries of Boost.Test
        if "unit_test_framework" in boost_dependencies.export.dependencies and "test" in module_provides_extra:
            boost_dependencies.export.dependencies["unit_test_framework"].extend(module_provides_extra["test"].difference({"unit_test_framework"}))

        # python and numpy have a version suffix. Add it here.
        if "python" in libraries:
            if len(libraries["python"]) != 1:
                raise Exception("Boost.Python should provide exactly one library")
            libraries["python"][0] += "{py_major}{py_minor}"
        if "numpy" in libraries:
            if len(libraries["numpy"]) != 1:
                raise Exception("Boost.Numpy should provide exactly one library")
            libraries["numpy"][0] += "{py_major}{py_minor}"

        boost_dependencies.export.libs = libraries
        boost_dependencies.export.static_only = [
            "boost_exception",
            "boost_test_exec_monitor",
        ]

        return boost_dependencies

    @property
    def _outputpath(self) -> Path:
        return script_dir / "dependencies" / f"dependencies-{self.boost_version}.yml"

    @classmethod
    def _sort_item(cls, item):
        if isinstance(item, dict):
            items = sorted(item.items())
            new_items = []
            for item in sorted(items):
                new_items.append((item[0], cls._sort_item(item[1])))
            return dict(new_items)
        elif isinstance(item, tuple):
            return tuple(cls._sort_item(e) for e in sorted(item))
        elif isinstance(item, list):
            return list(cls._sort_item(e) for e in sorted(item))
        else:
            return item

    def do_create_dependency_file(self) -> None:
        tree = self.do_boostdep_collect()
        tree = self.do_create_libraries(tree)

        tree.export.dependencies = self._fix_dependencies(tree.export.dependencies)
        data = dataclasses.asdict(tree.export)

        # Manual fixes for Conan
        if Version(self.boost_version) >= "1.81.0":
            data["requirements"]["locale"].append("iconv")

        data = self._sort_item(data)

        print(f"Creating {self._outputpath}")
        with self._outputpath.open("w") as fout:
            yaml.dump(data, fout)


def main(argv=None):
    parser = argparse.ArgumentParser()
    version_group = parser.add_mutually_exclusive_group(required=True)
    version_group.add_argument("-v", dest="boost_version", help="boost version")
    version_group.add_argument("-A", dest="boost_version", action="store_const", const=None, help="All boost versions")
    parser.add_argument("--verbose", dest="verbose", action="store_true", help="verbose output")
    parser.add_argument("-d", dest="boostdep_version", default="[*]", type=str, help="boostdep version")
    parser.add_argument("-u", dest="git_url", default=BOOST_GIT_URL, help="boost git url")
    ns = parser.parse_args(argv)

    logging.basicConfig(format="[%(levelname)s] %(message)s")
    if ns.verbose:
        log.setLevel(logging.DEBUG)

    if ns.boost_version is None:
        conan_data = yaml.safe_load(Path("conandata.yml").open())
        boost_versions = list(conan_data["sources"].keys())
    else:
        boost_versions = [ns.boost_version]

    for boost_version in boost_versions:
        print(f"Starting {boost_version}")
        with tempfile.TemporaryDirectory() as tmppath:
            boost_collector = BoostDependencyBuilder(
                boost_version=boost_version,
                boostdep_version=ns.boostdep_version,
                git_url=ns.git_url,
                tmppath=tmppath,
            )
            boost_collector.do_git_clone()
            boost_collector.do_install_boostdep()
            boost_collector.do_create_dependency_file()


if __name__ == "__main__":
    main()
