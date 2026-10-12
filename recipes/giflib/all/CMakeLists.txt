cmake_minimum_required(VERSION 3.15)
project(gif LANGUAGES C)

include(GNUInstallDirs)

add_library(gif
    dgif_lib.c
    egif_lib.c
    gifalloc.c
    gif_err.c
    gif_font.c
    gif_hash.c
    openbsd-reallocarray.c
    quantize.c
)
if(WIN32)
    if(BUILD_SHARED_LIBS)
        set_property(TARGET gif PROPERTY PREFIX )
        target_compile_definitions(gif INTERFACE USE_GIF_DLL)
    else()
        target_compile_definitions(gif PUBLIC USE_GIF_LIB)
    endif()
endif()

install(
    TARGETS gif
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(
    FILES gif_lib.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

if(UTILS)
    add_library(giflib_util STATIC
        qprintf.c
        getarg.c
    )
    target_link_libraries(giflib_util PRIVATE gif)

    set(GIF_UTILS
        gif2rgb
        gifbuild
        giffix
        giftext
        giftool
        gifclrmp
    )
    foreach(GIF_UTIL ${GIF_UTILS})
        add_executable(${GIF_UTIL} ${GIF_UTIL}.c)
        target_link_libraries(${GIF_UTIL} PRIVATE gif giflib_util)
    endforeach()
    include(CheckLibraryExists)
    check_library_exists(m pow "" LIBM)
    target_link_libraries(gifclrmp PRIVATE $<$<BOOL:${LIBM}>:m>)
    if(MSVC)
        find_package(getopt-for-visual-studio REQUIRED CONFIG)
        target_link_libraries(giftool PRIVATE getopt-for-visual-studio::getopt-for-visual-studio)
    endif()
    install(TARGETS ${GIF_UTILS} DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
