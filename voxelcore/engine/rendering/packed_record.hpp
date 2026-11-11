// PROJECT VOXELCORE — E7 packed quad record codec (8 bytes, chunk-local).
// Layout (see docs/design/E7_PACKED_RECORDS.md):
//   word0: x:4 | z:4 | y:6 | uExt-1:4 | vExt-1:4 | dir:3 | reserved:7
//   word1: block:16 | ao[4]x2b:8 | light:4 | reserved:4
// Plane positions are stored as SLICE INDICES (0..15 x/z, 0..63 y); the actual plane =
// slice + (dir is a positive direction ? 1 : 0). This fits boundary planes (x/z=16, y=64) in 6 bits.
#pragma once

#include "../meshing/mesher.hpp"
#include <cstdint>
#include <array>
#include <optional>
#include <vector>

namespace vc {

struct QuadRecord {
    std::uint8_t x = 0, z = 0;   // [0,15]
    std::uint8_t y = 0;          // [0,63] slice index; plane = y + (PosY ? 1 : 0)
    std::uint8_t uExt = 1, vExt = 1; // [1,16]
    FaceDir dir = FaceDir::PosY;
    BlockId block = 0;
    std::array<std::uint8_t, 4> ao = {3, 3, 3, 3}; // 0..3 each
    std::uint8_t light = 15;                        // 0..15
};

struct PackedRecord { std::uint32_t w0 = 0, w1 = 0; };

[[nodiscard]] inline std::optional<PackedRecord> packRecord(const QuadRecord& r) {
    if (r.x > 15 || r.z > 15 || r.y > 63) return std::nullopt;
    if (r.uExt < 1 || r.uExt > 16 || r.vExt < 1 || r.vExt > 16) return std::nullopt;
    const std::uint32_t dir = static_cast<std::uint32_t>(r.dir);
    if (dir > 5) return std::nullopt;
    // BlockId is 16-bit; no range check needed beyond the cast.
    for (std::uint8_t a : r.ao) if (a > 3) return std::nullopt;
    if (r.light > 15) return std::nullopt;
    std::uint32_t w0 = 0;
    w0 |= static_cast<std::uint32_t>(r.x);
    w0 |= static_cast<std::uint32_t>(r.z) << 4;
    w0 |= static_cast<std::uint32_t>(r.y) << 8;
    w0 |= static_cast<std::uint32_t>(r.uExt - 1) << 14;
    w0 |= static_cast<std::uint32_t>(r.vExt - 1) << 18;
    w0 |= dir << 22;
    std::uint32_t w1 = 0;
    w1 |= static_cast<std::uint32_t>(r.block);
    for (int i = 0; i < 4; ++i) w1 |= static_cast<std::uint32_t>(r.ao[i]) << (16 + 2 * i);
    w1 |= static_cast<std::uint32_t>(r.light) << 24;
    return PackedRecord{w0, w1};
}

[[nodiscard]] inline QuadRecord unpackRecord(const PackedRecord& rec) {
    QuadRecord r;
    r.x = static_cast<std::uint8_t>(rec.w0 & 0xF);
    r.z = static_cast<std::uint8_t>((rec.w0 >> 4) & 0xF);
    r.y = static_cast<std::uint8_t>((rec.w0 >> 8) & 0x3F);
    r.uExt = static_cast<std::uint8_t>(((rec.w0 >> 14) & 0xF) + 1);
    r.vExt = static_cast<std::uint8_t>(((rec.w0 >> 18) & 0xF) + 1);
    r.dir = static_cast<FaceDir>((rec.w0 >> 22) & 0x7);
    r.block = static_cast<BlockId>(rec.w1 & 0xFFFF);
    for (int i = 0; i < 4; ++i) r.ao[i] = static_cast<std::uint8_t>((rec.w1 >> (16 + 2 * i)) & 0x3);
    r.light = static_cast<std::uint8_t>((rec.w1 >> 24) & 0xF);
    return r;
}

// Converts an absolute-coordinate mesher quad to a chunk-local record (chunk origin absolute voxels).
// Plane position is stored as the SLICE index (plane = slice + (positive dir ? 1 : 0));
// x/z store the in-plane min corner for PosY/NegY faces, and (plane-slice, in-plane min-z) for x/z faces.
[[nodiscard]] inline std::optional<PackedRecord> packQuadLocal(const Quad& q, int chunkOriginX, int chunkOriginZ) {
    QuadRecord r;
    const int lx = static_cast<int>(q.x) - chunkOriginX;
    const int lz = static_cast<int>(q.z) - chunkOriginZ;
    switch (q.dir) {
        case FaceDir::PosX:
            r.x = static_cast<std::uint8_t>(lx - 1);  // plane was slice+1; recover slice
            r.z = static_cast<std::uint8_t>(lz);
            break;
        case FaceDir::NegX:
            r.x = static_cast<std::uint8_t>(lx);
            r.z = static_cast<std::uint8_t>(lz);
            break;
        case FaceDir::PosZ:
            r.x = static_cast<std::uint8_t>(lx);
            r.z = static_cast<std::uint8_t>(lz - 1);  // plane z = slice+1; recover slice
            break;
        case FaceDir::NegZ:
            r.x = static_cast<std::uint8_t>(lx);
            r.z = static_cast<std::uint8_t>(lz);
            break;
        case FaceDir::PosY:
            r.x = static_cast<std::uint8_t>(lx);
            r.z = static_cast<std::uint8_t>(lz);
            break;
        case FaceDir::NegY:
            r.x = static_cast<std::uint8_t>(lx);
            r.z = static_cast<std::uint8_t>(lz);
            break;
    }
    r.y = static_cast<std::uint8_t>(q.dir == FaceDir::PosY ? static_cast<int>(q.y) - 1 : static_cast<int>(q.y));
    r.uExt = static_cast<std::uint8_t>(q.u);
    r.vExt = static_cast<std::uint8_t>(q.v);
    r.dir = q.dir;
    r.block = q.block;
    r.ao = q.ao;
    r.light = q.light;
    return packRecord(r);
}

// Side faces may merge taller than 16 blocks vertically (v up to 64) but records store 4-bit extents.
// Every cell in a greedy-merged rectangle is cellEqual (block/light/ao all identical), so a vertical
// split into <=16-row sub-rects reuses q.ao[4]/q.light verbatim — the split is exact, not approximate.
[[nodiscard]] inline std::optional<std::vector<PackedRecord>> packQuadLocalMulti(const Quad& q, int chunkOriginX, int chunkOriginZ) {
    std::vector<PackedRecord> out;
    const bool sideFace = (q.dir == FaceDir::PosX || q.dir == FaceDir::NegX ||
                           q.dir == FaceDir::PosZ || q.dir == FaceDir::NegZ);
    if (!sideFace || q.v <= 16.0f) {
        if (const auto p = packQuadLocal(q, chunkOriginX, chunkOriginZ)) out.push_back(*p); else return std::nullopt;
        return out;
    }
    int remaining = static_cast<int>(q.v);
    float y = q.y;
    while (remaining > 16) {
        Quad sub = q; sub.y = y; sub.v = 16.0f;
        if (const auto p = packQuadLocal(sub, chunkOriginX, chunkOriginZ)) out.push_back(*p); else return std::nullopt;
        remaining -= 16; y += 16.0f;
    }
    if (remaining > 0) {
        Quad sub = q; sub.y = y; sub.v = static_cast<float>(remaining);
        if (const auto p = packQuadLocal(sub, chunkOriginX, chunkOriginZ)) out.push_back(*p); else return std::nullopt;
    }
    return out;
}

} // namespace vc

namespace vc {

// Plane position encoded in a record (chunk-local units; add chunk origin for absolute).
// Pos* planes lie at slice+1; Neg* planes lie at slice itself.
inline float planeLocal(FaceDir d, const QuadRecord& r) {
    switch (d) {
        case FaceDir::PosX: return static_cast<float>(r.x) + 1.0f;
        case FaceDir::NegX: return static_cast<float>(r.x);
        case FaceDir::PosZ: return static_cast<float>(r.z) + 1.0f;
        case FaceDir::NegZ: return static_cast<float>(r.z);
        case FaceDir::PosY: return static_cast<float>(r.y) + 1.0f;
        case FaceDir::NegY: return static_cast<float>(r.y);
    }
    return 0.0f;
}

} // namespace vc
