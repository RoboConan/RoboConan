cmake_minimum_required(VERSION 3.15)
project(test_package)

find_package(SDL2 REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
if(TARGET SDL2::SDL2main)
    target_link_libraries(${PROJECT_NAME} SDL2::SDL2main)
endif()
if(TARGET SDL2::SDL2-static)
    target_link_libraries(${PROJECT_NAME} SDL2::SDL2-static)
else()
    target_link_libraries(${PROJECT_NAME} SDL2::SDL2)
endif()
