cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(gRPC CONFIG REQUIRED)

add_executable(${PROJECT_NAME} test_package.cpp helloworld.proto)
target_link_libraries(${PROJECT_NAME}
    PRIVATE
        gRPC::grpc++
)
target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
protobuf_generate(
    TARGET ${PROJECT_NAME}
    LANGUAGE cpp
)
protobuf_generate(
    TARGET ${PROJECT_NAME}
    LANGUAGE grpc
    GENERATE_EXTENSIONS .grpc.pb.h .grpc.pb.cc
    PLUGIN protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>
)
