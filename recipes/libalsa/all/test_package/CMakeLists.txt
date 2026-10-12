cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(ALSA REQUIRED)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE ALSA::ALSA)

add_executable(test_package_atopology test_package_atopology.c)
target_link_libraries(test_package_atopology PRIVATE ALSA::atopology)
