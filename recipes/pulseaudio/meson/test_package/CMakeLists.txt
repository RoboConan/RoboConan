cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(PulseAudio REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE pulseaudio::pulse pulseaudio::pulse-simple)
if(TARGET pulseaudio::pulse-mainloop-glib)
    target_link_libraries(${PROJECT_NAME} PRIVATE pulseaudio::pulse-mainloop-glib)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_PULSE_GLIB)
endif()
