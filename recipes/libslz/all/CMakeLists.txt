cmake_minimum_required(VERSION 3.15)
project(slz LANGUAGES C)

set(slz_sources src/src/slz.c)
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/src/src/slz_common.c")
    list(APPEND slz_sources src/src/slz_common.c src/src/uslz.c)
endif()

add_library(slz ${slz_sources})
include_directories(src/src)
set_target_properties(slz PROPERTIES
    PUBLIC_HEADER src/src/slz.h
    WINDOWS_EXPORT_ALL_SYMBOLS ON
    C_STANDARD 11
    C_EXTENSIONS ON
)

include(GNUInstallDirs)
install(
    TARGETS slz
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
