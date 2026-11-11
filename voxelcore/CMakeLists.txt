cmake_minimum_required(VERSION 3.21)
project(voxelcore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

add_compile_options(-Wall -Wextra -Wno-unused-parameter)
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_compile_options(-O3)
endif()

# Engine interface library (header-first for now; split into .cpp TUs as they grow).
add_library(voxelcore_engine INTERFACE)
target_include_directories(voxelcore_engine INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/engine)
find_package(Threads REQUIRED)
target_link_libraries(voxelcore_engine INTERFACE Threads::Threads)

add_executable(voxelcore tools/voxelcore-cli/main.cpp)
target_link_libraries(voxelcore PRIVATE voxelcore_engine)

add_executable(voxelcore_tests tests/test_main.cpp)
target_link_libraries(voxelcore_tests PRIVATE voxelcore_engine)

add_executable(voxelcore_bench benchmarks/bench_main.cpp)
target_link_libraries(voxelcore_bench PRIVATE voxelcore_engine)

enable_testing()
add_test(NAME unit COMMAND voxelcore_tests)
