include(CheckCXXSourceCompiles)
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

# zlib probe: try the unversioned name first, then the glibc soname.
set(_zlib_found FALSE)
foreach(_lib IN ITEMS "z" "-l:libz.so.1")
    set(CMAKE_REQUIRED_LIBRARIES "${_lib}")
    unset(VOXELCORE_ZLIB_WORKS CACHE)
    check_cxx_source_compiles("
extern \"C\" {
    unsigned long compressBound(unsigned long);
    int compress2(unsigned char*, unsigned long*, const unsigned char*, unsigned long, int);
    int uncompress(unsigned char*, unsigned long*, const unsigned char*, unsigned long);
    }
    int main() {
        unsigned char src[4] = {1,2,3,4}, dst[64], out[64];
        unsigned long dlen = sizeof(dst);
        if (compress2(dst, &dlen, src, sizeof(src), 6) != 0) return 1;
        unsigned long olen = sizeof(out);
        if (uncompress(out, &olen, dst, dlen) != 0) return 2;
        return out[0] == 1 ? 0 : 3;
    }" VOXELCORE_ZLIB_WORKS)
    if(VOXELCORE_ZLIB_WORKS)
        target_compile_definitions(voxelcore_engine INTERFACE VOXELCORE_HAVE_ZLIB)
        target_link_libraries(voxelcore_engine INTERFACE ${_lib})
        message(STATUS "zlib: found (${_lib})")
        set(_zlib_found TRUE)
        break()
    endif()
endforeach()
unset(CMAKE_REQUIRED_LIBRARIES)
if(NOT _zlib_found)
    message(WARNING "zlib: NOT found — region-file writes will fail at runtime; reads of compressed data will fail loudly")
endif()
target_link_libraries(voxelcore_engine INTERFACE Threads::Threads)

add_executable(voxelcore tools/voxelcore-cli/main.cpp)
target_link_libraries(voxelcore PRIVATE voxelcore_engine)

add_executable(voxelcore_tests tests/test_main.cpp)
target_link_libraries(voxelcore_tests PRIVATE voxelcore_engine)

add_executable(voxelcore_bench benchmarks/bench_main.cpp)
target_link_libraries(voxelcore_bench PRIVATE voxelcore_engine)

enable_testing()
add_test(NAME unit COMMAND voxelcore_tests)
