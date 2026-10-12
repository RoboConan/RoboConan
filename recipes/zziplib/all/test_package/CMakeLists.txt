cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(zziplib REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
foreach(component libzzip libzzipmmapped libzzipfseeko libzzipwrap)
    if(TARGET zziplib::${component})
        target_link_libraries(${PROJECT_NAME} PRIVATE zziplib::${component})
    endif()
endforeach()
