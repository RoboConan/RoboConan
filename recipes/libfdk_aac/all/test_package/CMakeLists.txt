cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(fdk-aac REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE FDK-AAC::fdk-aac)
target_compile_features(${PROJECT_NAME} PRIVATE c_std_99)

if(TARGET FDK-XHE-AAC::fdk-xhe-aac)
    add_executable(test_package_xhe test_package_xhe.c)
    target_link_libraries(test_package_xhe PRIVATE FDK-XHE-AAC::fdk-xhe-aac)
    target_compile_features(test_package_xhe PRIVATE c_std_99)
endif()
