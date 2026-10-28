from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type", "fortran"
    python_requires = "tested_reference_str"
    python_requires_extend = "conan-fortran.Fortran"

    def config_options(self):
        if self.settings.get_safe("fortran") is None:
            self.settings.rm_safe("fortran")

    def requirements(self):
        if self.settings.get_safe("fortran") is not None:
            self.fortran.requires_runtime()

    def test(self):
        module = self.python_requires["conan-fortran"].module
        assert module.mangling_from_value("upper_no_underscore").autoconf == (
            "upper case, no underscore, no extra underscore"
        )
        override = self.conf.get(
            "user.conan-fortran:name_mangling", default=None, check_type=str
        )
        if override is not None:
            mangling = self.fortran.autoconf_mangling
            expected = {
                "lower_no_underscore": "lower case, no underscore, no extra underscore",
                "lower_underscore": "lower case, underscore, no extra underscore",
                "lower_underscore_extra": "lower case, underscore, extra underscore",
                "upper_no_underscore": "upper case, no underscore, no extra underscore",
                "upper_underscore": "upper case, underscore, no extra underscore",
                "upper_underscore_extra": "upper case, underscore, extra underscore",
            }[override]
            assert mangling == expected
            return
        if self.settings.get_safe("fortran") is None:
            assert self.fortran.autoconf_mangling == "lower case, underscore, no extra underscore"
            return
        self.fortran.validate_build()
        assert self.fortran.compiler == str(self.settings.fortran)
        assert self.fortran.executable
        assert str(self.fortran.version) == str(self.settings.fortran.version)
        assert self.fortran.std == (
            int(str(self.settings.fortran.std))
            if self.settings.get_safe("fortran.std") is not None else None
        )
        assert self.fortran.runtime == str(self.settings.fortran.runtime)
        if str(self.settings.fortran) in ["ifort", "ifx"] and self.settings.os == "Windows":
            assert self.fortran.autoconf_mangling == "upper case, no underscore, no extra underscore"
        else:
            assert self.fortran.autoconf_mangling == "lower case, underscore, no extra underscore"
        if self.settings.get_safe("fortran.std") is not None:
            self.fortran.check_min_fortran_std(self.settings.fortran.std)
            self.fortran.check_max_fortran_std(self.settings.fortran.std)
