import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class YandexOzoConan(ConanFile):
    name = "yandex-ozo"
    description = "C++ header-only library for asynchronous access to PostgreSQL databases using ASIO"
    license = "PostgreSQL"
    homepage = "https://github.com/yandex/ozo"
    topics = ("ozo", "yandex", "postgres", "postgresql", "cpp17", "database", "db", "asio", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        self.options["boost"].with_thread = True
        self.options["boost"].with_coroutine = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Used in ozo/detail/bind.h public header
        # version range matches resource_pool
        self.requires("boost/[^1.71.0 <1.81]", transitive_headers=True)
        self.requires("resource_pool/cci.20210322")
        self.requires("libpq/[^17.0]")

    def package_id(self):
        self.info.clear()

    def _validate_compiler_settings(self):
        check_min_cppstd(self, 17)

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("ozo does currently not support windows")

        self._validate_compiler_settings()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "*.h",
             dst=os.path.join(self.package_folder, "include", "ozo"),
             src=os.path.join(self.source_folder, "include", "ozo"))
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        main_comp = self.cpp_info.components["_ozo"]
        main_comp.requires = ["boost::boost", "boost::thread", "boost::coroutine", "resource_pool::resource_pool", "libpq::pq"]
        main_comp.defines = ["BOOST_HANA_CONFIG_ENABLE_STRING_UDL", "BOOST_ASIO_USE_TS_EXECUTOR_AS_DEFAULT"]
        main_comp.set_property("cmake_target_name", "yandex::ozo")

        compiler = self.settings.compiler
        version = Version(compiler.version)
        if compiler == "clang" or compiler == "apple-clang" or (compiler == "gcc" and version >= 9):
            main_comp.cxxflags = ["-Wno-gnu-string-literal-operator-template", "-Wno-gnu-zero-variadic-macro-arguments"]

        self.cpp_info.set_property("cmake_file_name", "ozo")
        self.cpp_info.set_property("cmake_target_name", "yandex::ozo")
