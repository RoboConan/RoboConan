cmake_minimum_required(VERSION 3.15)
project(bzip2 LANGUAGES C)

include(GNUInstallDirs)

option(BZ2_BUILD_EXE "Build bzip2 command-line utility" ON)

add_library(bz2
    blocksort.c
    bzlib.c
    compress.c
    crctable.c
    decompress.c
    huffman.c
    randtable.c
)

target_include_directories(bz2 PUBLIC ${BZ2_SRC_DIR})
set_target_properties(bz2
    PROPERTIES
    PUBLIC_HEADER "bzlib.h"
    SOVERSION ${BZ2_VERSION_MAJOR}.0
    VERSION ${BZ2_VERSION_STRING}
    WINDOWS_EXPORT_ALL_SYMBOLS ON
)

install(
    TARGETS bz2
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

if(BZ2_BUILD_EXE)
    add_executable(bzip2 bzip2.c)
    target_link_libraries(bzip2 PRIVATE bz2)
    install(TARGETS bzip2 DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
