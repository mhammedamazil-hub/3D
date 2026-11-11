// PROJECT VOXELCORE — zlib wrapper for Anvil region compression.
// Links directly against libz (stable ABI; present in glibc systems and the Android NDK).
// Configure-time probe (see CMakeLists) defines VOXELCORE_HAVE_ZLIB; when absent,
// region WRITES fail loudly and reads of compressed data fail rather than corrupt.
#pragma once

#include <cstdint>
#include <vector>
#include <string>

#if defined(VOXELCORE_HAVE_ZLIB)
extern "C" {
unsigned long compressBound(unsigned long sourceLen);
int compress2(unsigned char* dest, unsigned long* destLen, const unsigned char* source, unsigned long sourceLen, int level);
int uncompress(unsigned char* dest, unsigned long* destLen, const unsigned char* source, unsigned long sourceLen);
}
namespace vc { inline constexpr bool kZlibAvailable = true; }
#else
namespace vc { inline constexpr bool kZlibAvailable = false; }
#endif

namespace vc {

struct ZlibResult {
    bool ok = false;
    std::string error;
};

inline ZlibResult zlibCompress(const std::uint8_t* src, std::size_t srcLen, std::vector<std::uint8_t>& out, int level = 6) {
#if defined(VOXELCORE_HAVE_ZLIB)
    const unsigned long bound = compressBound(static_cast<unsigned long>(srcLen));
    out.resize(bound);
    unsigned long dlen = bound;
    const int rc = compress2(out.data(), &dlen, src, static_cast<unsigned long>(srcLen), level);
    if (rc != 0) return {false, "compress2 rc=" + std::to_string(rc)};
    out.resize(dlen);
    return {true, {}};
#else
    (void)src; (void)srcLen; (void)out; (void)level;
    return {false, "zlib not available at configure time"};
#endif
}

inline ZlibResult zlibUncompress(const std::uint8_t* src, std::size_t srcLen, std::vector<std::uint8_t>& out, std::size_t expectedSize) {
#if defined(VOXELCORE_HAVE_ZLIB)
    out.resize(expectedSize);
    unsigned long dlen = static_cast<unsigned long>(expectedSize);
    const int rc = uncompress(out.data(), &dlen, src, static_cast<unsigned long>(srcLen));
    if (rc != 0) return {false, "uncompress rc=" + std::to_string(rc)};
    out.resize(dlen);
    return {true, {}};
#else
    (void)src; (void)srcLen; (void)out; (void)expectedSize;
    return {false, "zlib not available at configure time"};
#endif
}

} // namespace vc
