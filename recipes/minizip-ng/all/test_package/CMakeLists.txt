cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(minizip-ng QUIET CONFIG)
if(TARGET MINIZIP::minizip-ng)
    set(minizip_target MINIZIP::minizip-ng)
else()
    find_package(minizip REQUIRED CONFIG)
    set(minizip_target MINIZIP::minizip)
endif()

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE ${minizip_target})
target_compile_features(${PROJECT_NAME} PRIVATE c_std_99)
