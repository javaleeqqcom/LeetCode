cmake_minimum_required(VERSION 3.16)
project(oj_native_manager LANGUAGES CXX)

if(NOT WIN32)
    message(FATAL_ERROR "The current native sandbox manager targets Windows only")
endif()

add_executable(oj_native_manager src/process_manager.cpp)
target_compile_features(oj_native_manager PRIVATE cxx_std_11)
target_compile_definitions(oj_native_manager PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

if(MINGW)
    target_link_options(oj_native_manager PRIVATE -static-libgcc -static-libstdc++)
endif()
