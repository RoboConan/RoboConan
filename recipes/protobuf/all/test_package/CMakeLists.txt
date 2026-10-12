cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(protobuf CONFIG REQUIRED)

add_executable(${PROJECT_NAME} test_package.cpp)

if (TARGET protobuf::libprotobuf-lite)
    target_link_libraries(${PROJECT_NAME} PRIVATE protobuf::libprotobuf-lite)
    target_compile_definitions(${PROJECT_NAME} PRIVATE CONANTEST_PROTOBUF_LITE=1)
else()
    target_link_libraries(${PROJECT_NAME} PRIVATE protobuf::libprotobuf)
endif()

if(NOT TARGET protobuf::protoc)
    message(FATAL_ERROR "protoc executable should have been defined as part of find_package(protobuf)")
endif()

if(NOT COMMAND protobuf_generate)
    message(FATAL_ERROR "protobuf_generate should have been defined as part of find_package(protobuf)")
endif()

if(NOT TARGET protobuf::libprotobuf-lite)
    target_sources(${PROJECT_NAME} PRIVATE addressbook.proto)
    protobuf_generate(TARGET ${PROJECT_NAME} LANGUAGE cpp)
    target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
endif()
