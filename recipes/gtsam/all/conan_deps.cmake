find_package(spectra REQUIRED CONFIG)

# GTSAM 4.2 has no system-Spectra option, so its source is patched to include
# Spectra headers and all targets need the include path while they build.
if(NOT GTSAM_USE_SYSTEM_SPECTRA)
    link_libraries(Spectra::Spectra)
endif()

if(GTSAM_CONAN_WITH_CHOLMOD)
    find_package(CHOLMOD REQUIRED CONFIG)
endif()

if(GTSAM_ENABLE_CUDSS)
    find_package(cudss REQUIRED CONFIG)
endif()
