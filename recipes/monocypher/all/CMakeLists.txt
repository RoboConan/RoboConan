cmake_minimum_required(VERSION 3.15)
project(monocypher LANGUAGES C)

set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)

option(MONOCYPHER_ED25519 "Build optional Ed25519 support" ON)

add_library(monocypher src/monocypher.c)
target_include_directories(monocypher PUBLIC src)
if(MONOCYPHER_ED25519)
    target_sources(monocypher PRIVATE src/optional/monocypher-ed25519.c)
endif()

if(NOT MSVC)
    target_compile_options(monocypher PRIVATE -Wall -Wextra -pedantic)
endif()

string(REGEX MATCH "^[0-9]+" MONOCYPHER_SOVERSION "${MONOCYPHER_VERSION}")
set_target_properties(monocypher PROPERTIES
    VERSION "${MONOCYPHER_VERSION}"
    SOVERSION "${MONOCYPHER_SOVERSION}"
)

install(TARGETS monocypher
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)
install(FILES src/monocypher.h DESTINATION include)
if(MONOCYPHER_ED25519)
    install(FILES src/optional/monocypher-ed25519.h DESTINATION include)
endif()
