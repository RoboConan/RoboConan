cmake_minimum_required(VERSION 3.15)
project(tinyexr LANGUAGES C)

file(GLOB tinyexr_sources CONFIGURE_DEPENDS "${TINYEXR_SRC_DIR}/src/*.c")
add_library(tinyexr3 ${tinyexr_sources} "${TINYEXR_SRC_DIR}/deps/zstd/tinyexr_zstd.c")
set_target_properties(tinyexr3 PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED ON
    C_EXTENSIONS OFF
    VERSION ${TINYEXR_VERSION}
    SOVERSION 3
    WINDOWS_EXPORT_ALL_SYMBOLS ON
)
target_include_directories(tinyexr3
    PUBLIC $<BUILD_INTERFACE:${TINYEXR_SRC_DIR}/include>
           $<INSTALL_INTERFACE:include>
    PRIVATE "${TINYEXR_SRC_DIR}/src" "${TINYEXR_SRC_DIR}/deps/zstd"
)

if(TINYEXR_WITH_LIBDEFLATE)
    find_package(libdeflate REQUIRED CONFIG)
    target_compile_definitions(tinyexr3 PRIVATE
        EXR_USE_LIBDEFLATE
        EXR_ZLIB_DEFAULT_LIBDEFLATE=1
    )
    target_link_libraries(tinyexr3 PRIVATE libdeflate::libdeflate)
endif()

if(TINYEXR_WITH_THREADS)
    find_package(Threads REQUIRED)
    target_compile_definitions(tinyexr3 PRIVATE EXR_USE_THREADS)
    target_link_libraries(tinyexr3 PRIVATE Threads::Threads)
endif()

install(TARGETS tinyexr3
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)
install(FILES
    "${TINYEXR_SRC_DIR}/include/exr.h"
    "${TINYEXR_SRC_DIR}/include/exr_gpu.h"
    "${TINYEXR_SRC_DIR}/include/exr_vk.h"
    DESTINATION include
)
