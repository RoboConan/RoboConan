cmake_minimum_required(VERSION 3.15)
project(CSDP LANGUAGES C)

set(CMAKE_C_STANDARD 99 CACHE STRING "C standard to use")
set(CMAKE_C_STANDARD_REQUIRED ON)

set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS TRUE)

option(CSDP_USE_OPENMP "Enable OpenMP support" ON)
option(CSDP_BUILD_SOLVER "Build the main CSDP solver executable" ON)
option(CSDP_BUILD_THETA "Build theta graph theory tools" ON)

find_package(BLAS REQUIRED)
find_package(LAPACK REQUIRED)

add_compile_definitions(BIT64)

if(NOT MSVC)
    add_compile_definitions(USEGETTIME)
endif()

if(UNIX AND NOT APPLE AND NOT CYGWIN)
    add_compile_definitions(USESIGTERM)
endif()

include_directories(include)

file(GLOB CSDP_SOURCES lib/*.c)
add_library(csdp ${CSDP_SOURCES})
target_link_libraries(csdp PUBLIC ${BLAS_LIBRARIES} ${LAPACK_LIBRARIES})
if(MSVC)
    target_compile_definitions(csdp PRIVATE strcasecmp=_stricmp)
endif()

include(CheckLibraryExists)
check_library_exists(m log "" CAN_LINK_LIBM)
if(CAN_LINK_LIBM)
    target_link_libraries(csdp PUBLIC m)
endif()

if(CSDP_USE_OPENMP)
    find_package(OpenMP REQUIRED)
    target_link_libraries(csdp PUBLIC OpenMP::OpenMP_C)
    target_compile_definitions(csdp PUBLIC USEOPENMP SETNUMTHREADS)
endif()

if(CSDP_BUILD_SOLVER)
    add_executable(csdp_solver solver/csdp.c)
    target_link_libraries(csdp_solver PRIVATE csdp)
    set_target_properties(csdp_solver PROPERTIES OUTPUT_NAME csdp)
    install(TARGETS csdp_solver DESTINATION bin)
endif()

if(CSDP_BUILD_THETA)
    add_executable(theta theta/theta.c)
    target_link_libraries(theta PRIVATE csdp)

    add_executable(complement theta/complement.c)
    target_link_libraries(complement PRIVATE csdp)

    add_executable(rand_graph theta/rand_graph.c)
    target_link_libraries(rand_graph PRIVATE csdp)

    add_executable(graphtoprob theta/graphtoprob.c)
    target_link_libraries(graphtoprob PRIVATE csdp)

    install(TARGETS theta complement rand_graph graphtoprob DESTINATION bin)
endif()

install(TARGETS csdp
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
        RUNTIME DESTINATION bin)

install(DIRECTORY include/
        DESTINATION include/csdp
        FILES_MATCHING PATTERN "*.h")

install(DIRECTORY matlab/
        DESTINATION lib/matlab/csdp
        FILES_MATCHING PATTERN "*.m")
