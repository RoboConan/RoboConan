cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(symphony REQUIRED IMPORTED_TARGET symphony)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE PkgConfig::symphony)

if(TEST_APPLICATION_LIBRARY)
    pkg_check_modules(symphony_app REQUIRED IMPORTED_TARGET symphony-app)
    add_executable(test_application test_package.c)
    target_link_libraries(test_application PRIVATE PkgConfig::symphony_app)
endif()
