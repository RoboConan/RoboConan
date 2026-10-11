cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(volk REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
set_source_files_properties(test_package.c PROPERTIES LANGUAGE CXX)
target_link_libraries(${PROJECT_NAME} PRIVATE volk::volk)

add_executable(${PROJECT_NAME}_nolibs test_package.c)
target_compile_definitions(${PROJECT_NAME}_nolibs PRIVATE VOLK_IMPLEMENTATION)
target_link_libraries(${PROJECT_NAME}_nolibs PRIVATE volk::volk_headers)
