cmake_minimum_required(VERSION 3.15)
project(LibRaw LANGUAGES CXX)

option(LIBRAW_BUILD_THREAD_SAFE "Build raw_r library with -pthread enabled" OFF)
option(LIBRAW_WITH_OPENMP "Build with OpenMP" ON)
option(LIBRAW_WITH_JPEG "Build with libjpeg" ON)
option(LIBRAW_WITH_LCMS "Build with LCMS" ON)
option(LIBRAW_WITH_ZLIB "Build with zlib" ON)

if(RAW_LIB_VERSION_STRING VERSION_LESS 0.21)
    set(libraw_LIB_SRCS ${LIBRAW_SRC_DIR}/internal/dcraw_common.cpp
                        ${LIBRAW_SRC_DIR}/internal/dcraw_fileio.cpp
                        ${LIBRAW_SRC_DIR}/internal/demosaic_packs.cpp
                        ${LIBRAW_SRC_DIR}/src/libraw_cxx.cpp
                        ${LIBRAW_SRC_DIR}/src/libraw_c_api.cpp
                        ${LIBRAW_SRC_DIR}/src/libraw_datastream.cpp
    )
else()
    file(GLOB_RECURSE libraw_LIB_SRCS CONFIGURE_DEPENDS "${LIBRAW_SRC_DIR}/src/*.cpp")

    # Exclude placeholder (stub) implementations
    file(GLOB_RECURSE exclude_libraw_LIB_SRCS CONFIGURE_DEPENDS "${LIBRAW_SRC_DIR}/src/*_ph.cpp")
    list(REMOVE_ITEM libraw_LIB_SRCS ${exclude_libraw_LIB_SRCS})
endif()

if(LIBRAW_WITH_JPEG)
    find_package(JPEG REQUIRED)
endif()
if(LIBRAW_WITH_LCMS)
    find_package(lcms REQUIRED CONFIG)
endif()
if(LIBRAW_WITH_OPENMP)
    find_package(OpenMP REQUIRED COMPONENTS CXX)
endif()
if(LIBRAW_WITH_ZLIB)
    find_package(ZLIB REQUIRED)
endif()

function(_configure_libraw_target target thread_safe)
    set_target_properties(${target} PROPERTIES
        VERSION ${RAW_LIB_VERSION}
        SOVERSION ${RAW_LIB_SOVERSION})
    target_compile_features(${target} PUBLIC cxx_std_11)
    target_include_directories(${target} PUBLIC "${LIBRAW_SRC_DIR}")
    if(WIN32)
        target_link_libraries(${target} PUBLIC ws2_32)
        if(BUILD_SHARED_LIBS)
            target_compile_definitions(${target} PRIVATE LIBRAW_BUILDLIB)
        else()
            target_compile_definitions(${target} PUBLIC LIBRAW_NODLL)
        endif()
    endif()
    if(MSVC)
        target_compile_options(${target} PRIVATE /wd4018 /wd4101 /wd4244 /wd4251 /wd4267 /wd4996)
    endif()
    if(NOT thread_safe)
        target_compile_definitions(${target} PRIVATE LIBRAW_NOTHREADS)
    elseif(NOT WIN32)
        find_package(Threads REQUIRED)
        target_link_libraries(${target} PUBLIC Threads::Threads)
    endif()
    if(LIBRAW_WITH_OPENMP)
        target_link_libraries(${target} PUBLIC OpenMP::OpenMP_CXX)
    endif()
    if(LIBRAW_WITH_JPEG)
        target_compile_definitions(${target} PRIVATE USE_JPEG USE_JPEG8)
        target_link_libraries(${target} PUBLIC JPEG::JPEG)
    endif()
    if(LIBRAW_WITH_LCMS)
        target_compile_definitions(${target} PRIVATE USE_LCMS2)
        target_link_libraries(${target} PUBLIC lcms::lcms)
    endif()
    if(LIBRAW_WITH_ZLIB)
        target_compile_definitions(${target} PRIVATE USE_ZLIB)
        target_link_libraries(${target} PUBLIC ZLIB::ZLIB)
    endif()
    if(DEFINED LIBRAW_MAX_CR3_RAW_FILE_SIZE)
        target_compile_definitions(${target} PRIVATE
            LIBRAW_MAX_CR3_RAW_FILE_SIZE=${LIBRAW_MAX_CR3_RAW_FILE_SIZE}LL)
    endif()
endfunction()

add_library(raw ${libraw_LIB_SRCS})
_configure_libraw_target(raw FALSE)

include(GNUInstallDirs)
if(LIBRAW_BUILD_THREAD_SAFE)
    add_library(raw_r ${libraw_LIB_SRCS})
    _configure_libraw_target(raw_r TRUE)
    install(
        TARGETS raw_r
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    )
endif()

install(DIRECTORY "${LIBRAW_SRC_DIR}/libraw" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(
    TARGETS raw
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
