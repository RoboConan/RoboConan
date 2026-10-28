cmake_minimum_required(VERSION 3.15)
project(nauty C)

add_library(nauty
    nauty.c
    nautil.c
    nausparse.c
    naugraph.c
    schreier.c
    naurng.c
    gtnauty.c
    nautinv.c
    gtools.c
)
set_target_properties(nauty PROPERTIES OUTPUT_NAME ${NAUTY_OUTPUT_NAME})

install(TARGETS nauty
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)
install(DIRECTORY ./ DESTINATION include/nauty FILES_MATCHING PATTERN "*.h")
