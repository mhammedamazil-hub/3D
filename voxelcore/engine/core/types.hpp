// PROJECT VOXELCORE — core value types.
// Data-oriented, allocation-free hot-path types shared by every subsystem.
#pragma once

#include <cstdint>
#include <cstddef>
#include <compare>
#include <functional>

namespace vc {

// A block id indexes the global block-state registry. 0 is always air.
using BlockId = std::uint16_t;
inline constexpr BlockId kAir = 0;
inline constexpr std::size_t kSectionSize = 16;             // 16 x 16 x 16 cells per section
inline constexpr std::size_t kSectionVolume = kSectionSize * kSectionSize * kSectionSize; // 4096
inline constexpr std::size_t kChunkSections = 4;            // 64 blocks of world height for now
inline constexpr int kChunkHeight = static_cast<int>(kSectionSize * kChunkSections);      // 64

// Section grid coordinates (a section is 16^3 blocks).
struct SectionPos {
    std::int32_t x = 0, y = 0, z = 0;
    constexpr bool operator==(const SectionPos&) const = default;
    constexpr auto operator<=>(const SectionPos&) const = default;
};

struct SectionPosHash {
    std::size_t operator()(const SectionPos& p) const noexcept {
        // 64-bit mix of the three coordinates (good enough distribution for hash maps).
        std::uint64_t h = static_cast<std::uint64_t>(static_cast<std::uint32_t>(p.x)) * 0x9E3779B97F4A7C15ull
                        ^ static_cast<std::uint64_t>(static_cast<std::uint32_t>(p.y)) * 0xC2B2AE3D27D4EB4Full
                        ^ static_cast<std::uint64_t>(static_cast<std::uint32_t>(p.z)) * 0x165667B19E3779F9ull;
        h ^= h >> 33; h *= 0xFF51AFD7ED558CCDull; h ^= h >> 33;
        return static_cast<std::size_t>(h);
    }
};

// Chunk column coordinates (a chunk is 16 x kChunkHeight x 16 blocks).
struct ChunkPos {
    std::int32_t x = 0, z = 0;
    constexpr bool operator==(const ChunkPos&) const = default;
    constexpr auto operator<=>(const ChunkPos&) const = default;
};

struct ChunkPosHash {
    std::size_t operator()(const ChunkPos& p) const noexcept {
        std::uint64_t h = static_cast<std::uint64_t>(static_cast<std::uint32_t>(p.x)) * 0x9E3779B97F4A7C15ull
                        ^ static_cast<std::uint64_t>(static_cast<std::uint32_t>(p.z)) * 0xC2B2AE3D27D4EB4Full;
        h ^= h >> 33; h *= 0xFF51AFD7ED558CCDull; h ^= h >> 33;
        return static_cast<std::size_t>(h);
    }
};

constexpr std::size_t sectionIndex(std::size_t x, std::size_t y, std::size_t z) noexcept {
    // y-major-then-z-then-x? We keep x-fastest for sequential access along rows.
    return (y * kSectionSize + z) * kSectionSize + x;
}

} // namespace vc
