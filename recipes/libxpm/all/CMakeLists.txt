cmake_minimum_required(VERSION 3.15)
project(libXpm VERSION "${CONAN_libXpm_VERSION}" LANGUAGES C)

add_library(Xpm
    src/Attrib.c
    src/CrBufFrI.c
    src/CrDatFrI.c
    src/create.c
    src/CrIFrBuf.c
    src/CrIFrDat.c
    src/data.c
    src/hashtab.c
    src/Image.c
    src/Info.c
    src/misc.c
    src/parse.c
    src/RdFToBuf.c
    src/RdFToDat.c
    src/RdFToI.c
    src/rgb.c
    src/scan.c
    src/WrFFrBuf.c
    src/WrFFrDat.c
    src/WrFFrI.c
)

if(UNIX)
  find_package(X11 REQUIRED)
  # Pixmap-related functions require X11 and are not available on Windows
  target_sources(Xpm PRIVATE
      src/CrBufFrP.c
      src/CrDatFrP.c
      src/CrIFrP.c
      src/CrPFrBuf.c
      src/CrPFrDat.c
      src/CrPFrI.c
      src/RdFToP.c
      src/WrFFrP.c
  )
  target_link_libraries(Xpm PRIVATE X11::X11)
endif()

if(WIN32)
  set_target_properties(Xpm PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS TRUE)
  target_compile_definitions(Xpm PRIVATE FOR_MSW)
endif()

if(MSVC)
  target_compile_definitions(
      Xpm PRIVATE
      _CRT_SECURE_NO_WARNINGS
      _CRT_NONSTDC_NO_DEPRECATE
  )
  target_compile_options(Xpm PRIVATE /wd4267 /wd4244 /wd4018)
endif()

target_include_directories(Xpm PRIVATE include/X11)

if(NOT WIN32)
    target_compile_definitions(Xpm PRIVATE
        # Build without the --enable-open-zfile option:
        # https://gitlab.freedesktop.org/xorg/lib/libxpm/-/blob/libXpm-3.5.17/configure.ac?ref_type=tags#L67-88
        NO_ZPIPE
    )
endif()

set_target_properties(
    Xpm PROPERTIES
    VERSION "${PROJECT_VERSION}"
    SOVERSION "${PROJECT_VERSION_MAJOR}"
)

# ---- Install ----

include(GNUInstallDirs)

install(
    TARGETS Xpm
    RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"
    LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
)

install(DIRECTORY include/X11 DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}")

