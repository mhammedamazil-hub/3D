// PROJECT VOXELCORE — sky/block light propagation, milestone M1 (stage 9).
//
// Semantics (Minecraft-compatible, simplified):
//   - Light is a 4-bit level per cell (0..15), stored as one byte per cell per channel.
//   - Sky seeding: every cell in an unobstructed vertical column (no opaque block above)
//     starts at 15; everything else starts at 0 and is filled by lateral flood fill.
//   - Flood fill relaxes neighbors with level-1, only through non-opaque blocks
//     (air, water, leaves). Opaque blocks always read 0.
//   - Water attenuates like air (opacity 1) in this M1; vanilla's opacity-1 default
//     matches that behavior. Face-directional "star" light and per-face AO tinting
//     from light are NOT applied yet (renderer integration is a later milestone).
//   - Boundary rule: lateral light entering from outside the region boundary is not
//     modeled; compute over the whole world (or a generous pad) when boundary caves
//     matter. Cells above the region top read as open sky (15) via skyAbove().
//
// Full-recompute design: analyze() computes one monolithic region; incremental
// "light removal + reflood" on block edits is a documented follow-up (needs a
// removal BFS + source heap, and interacts with mesh invalidation).
#pragma once

#include "../world/world.hpp"
#include "../world/block_reader.hpp"
#include "../chunks/block_ids.hpp"
#include <vector>
#include <cstdint>
#include <cstddef>
#include <deque>
#include <algorithm>
#include <limits>

namespace vc {

struct LightRegion {
    int x0 = 0, y0 = 0, z0 = 0;
    int sizeX = 16, sizeY = kChunkHeight, sizeZ = 16;
};

struct BlockLightSource {
    int x, y, z;
    std::uint8_t level; // 1..15
};

class LightVolume {
public:
    // Computes sky light for the region and (optionally) block light from `sources`.
    static LightVolume compute(const World& world, const LightRegion& region,
                               const std::vector<BlockLightSource>& sources = {}) {
        LightVolume v;
        v.region_ = region;
        const std::size_t count = static_cast<std::size_t>(region.sizeX) * region.sizeY * region.sizeZ;
        v.sky_.assign(count, 0);
        v.block_.assign(count, 0);
        std::vector<std::uint8_t> opaque(count, 0);
        const CachedBlockReader cached(world);
        const auto solidAt = [&](int x, int y, int z) {
            const bool o = blocks::opaque(cached(x, y, z));
            opaque[v.index(x, y, z)] = o ? 1 : 0;
            return o;
        };
        // --- sky seeding: column scan ---
        for (int z = region.z0; z < region.z0 + region.sizeZ; ++z)
            for (int x = region.x0; x < region.x0 + region.sizeX; ++x) {
                bool blocked = false;
                for (int y = region.y0 + region.sizeY - 1; y >= region.y0; --y) {
                    if (solidAt(x, y, z)) { blocked = true; v.sky_[v.index(x, y, z)] = 0; continue; }
                    v.sky_[v.index(x, y, z)] = blocked ? 0 : 15;
                }
            }
        v.flood(v.sky_, opaque);
        // --- block light seeding + flood ---
        for (const auto& src : sources) {
            if (!v.contains(src.x, src.y, src.z)) continue;
            if (blocks::opaque(cached(src.x, src.y, src.z))) continue; // sources occluded: no light
            const std::size_t i = v.index(src.x, src.y, src.z);
            v.block_[i] = std::max(v.block_[i], src.level);
        }
        v.flood(v.block_, opaque);
        return v;
    }

    // Lookup outside the region: above the top = open sky (15) / no light (0) for block;
    // sides and below = 0. Callers should not depend on side values for regions padded to the world AABB.
    std::uint8_t skyAt(int x, int y, int z) const {
        if (y >= region_.y0 + region_.sizeY) return 15;
        if (!contains(x, y, z)) return 0;
        return sky_[index(x, y, z)];
    }
    std::uint8_t blockAt(int x, int y, int z) const {
        if (!contains(x, y, z)) return 0;
        return block_[index(x, y, z)];
    }
    // Face light in [0,15] for shading a face at cell (x,y,z): max of both channels.
    std::uint8_t faceAt(int x, int y, int z) const { return std::max(skyAt(x, y, z), blockAt(x, y, z)); }

    std::size_t skylitCells() const {
        std::size_t n = 0;
        for (std::uint8_t v : sky_) if (v > 0) ++n;
        return n;
    }
    std::size_t blocklitCells() const {
        std::size_t n = 0;
        for (std::uint8_t v : block_) if (v > 0) ++n;
        return n;
    }
    const LightRegion& region() const { return region_; }

private:
    bool contains(int x, int y, int z) const {
        return x >= region_.x0 && x < region_.x0 + region_.sizeX
            && y >= region_.y0 && y < region_.y0 + region_.sizeY
            && z >= region_.z0 && z < region_.z0 + region_.sizeZ;
    }
    std::size_t index(int x, int y, int z) const {
        const std::size_t lx = static_cast<std::size_t>(x - region_.x0);
        const std::size_t ly = static_cast<std::size_t>(y - region_.y0);
        const std::size_t lz = static_cast<std::size_t>(z - region_.z0);
        return (ly * static_cast<std::size_t>(region_.sizeZ) + lz) * static_cast<std::size_t>(region_.sizeX) + lx;
    }

    // BFS flood fill: every cell relaxes its non-opaque neighbors with level-1.
    // Because attenuation is path-independent, the fixed point equals
    // level = 15 - shortest_path_through_nonopaque(seed). Only cells adjacent to the
    // lit/unlit boundary are enqueued initially (deep open sky has no relaxation work),
    // which cuts the common case to O(boundary) instead of O(region). `opaque` is a
    // precomputed 1-byte-per-cell flag vector — this function does no world lookups.
    void flood(std::vector<std::uint8_t>& light, const std::vector<std::uint8_t>& opaque) {
        const int sx = region_.sizeX, sy = region_.sizeY, sz = region_.sizeZ;
        const std::size_t span = static_cast<std::size_t>(sx) * sy * sz;
        const std::size_t plane = static_cast<std::size_t>(sx) * sz;
        std::deque<std::size_t> queue;
        for (std::size_t i = 0; i < span; ++i) {
            if (light[i] <= 1) continue;
            const std::size_t layer = i / plane, rem = i - layer * plane;
            const std::size_t lz = rem / static_cast<std::size_t>(sx), lx = rem - lz * sx;
            const std::size_t ly = layer;
            const std::size_t li = static_cast<std::size_t>(light[i]) - 1;
            // neighbor offsets in the flattened (ly, lz, lx) layout
            const std::size_t n[6] = {
                lx + 1 < static_cast<std::size_t>(sx) ? i + 1 : span, // +x
                lx >= 1                              ? i - 1 : span, // -x
                ly + 1 < static_cast<std::size_t>(sy) ? i + plane : span, // +y
                ly >= 1                               ? i - plane : span, // -y
                lz + 1 < static_cast<std::size_t>(sz) ? i + static_cast<std::size_t>(sx) : span, // +z
                lz >= 1                               ? i - static_cast<std::size_t>(sx) : span, // -z
            };
            for (int d = 0; d < 6; ++d) {
                const std::size_t ni = n[d];
                if (ni >= span) continue;
                if (opaque[ni]) continue;
                if (light[ni] < li) { queue.push_back(i); break; }
            }
        }
        while (!queue.empty()) {
            const std::size_t i = queue.front();
            queue.pop_front();
            const std::uint8_t level = light[i];
            if (level <= 1) continue;
            const std::size_t layer = i / plane, rem = i - layer * plane;
            const std::size_t lz = rem / static_cast<std::size_t>(sx), lx = rem - lz * sx;
            const std::size_t ly = layer;
            const std::size_t li = static_cast<std::size_t>(level) - 1;
            const std::size_t n[6] = {
                lx + 1 < static_cast<std::size_t>(sx) ? i + 1 : span,
                lx >= 1                              ? i - 1 : span,
                ly + 1 < static_cast<std::size_t>(sy) ? i + plane : span,
                ly >= 1                               ? i - plane : span,
                lz + 1 < static_cast<std::size_t>(sz) ? i + static_cast<std::size_t>(sx) : span,
                lz >= 1                               ? i - static_cast<std::size_t>(sx) : span,
            };
            for (int d = 0; d < 6; ++d) {
                const std::size_t ni = n[d];
                if (ni >= span) continue;
                if (opaque[ni]) continue;
                if (light[ni] >= li) continue;
                light[ni] = static_cast<std::uint8_t>(li);
                queue.push_back(ni);
            }
        }
    }

    LightRegion region_;
    std::vector<std::uint8_t> sky_, block_;
};

} // namespace vc
