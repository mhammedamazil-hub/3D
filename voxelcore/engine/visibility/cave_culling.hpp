// PROJECT VOXELCORE — cave culling (sealed-air face culling).
//
// Flood-fill from the world-AABB boundary over non-opaque cells. Component 0 = reachable
// from outside (the surface world). Sealed components (a cave fully enclosed by opaque
// blocks) get ids >= 1. A face whose adjacent non-opaque cell belongs to a sealed
// component is emitted only when the camera is inside the SAME component.
//
// This mirrors Horizon's cave culling: faces visible from nowhere reachable are not
// submitted. Correctness is preserved by construction — a camera inside a sealed cave
// sees its own component's faces.
//
// World AABB boundary handling: cells are treated as existing only within the loaded
// chunk bounds; the AABB surface is where "outside" connects. Analyze once per world
// change (block edits), not per frame.
#pragma once

#include "../world/world.hpp"
#include "../chunks/block_ids.hpp"
#include <cstdint>
#include <unordered_map>
#include <vector>
#include <deque>
#include <limits>

namespace vc {

class CaveCuller {
public:
    struct Bounds { int minX, minY, minZ, maxX, maxY, maxZ; }; // inclusive, world coords

    // Analyze all loaded chunks of `world`. Cost O(non-opaque cells).
    static CaveCuller analyze(const World& world) {
        CaveCuller c;
        if (world.chunks().empty()) { c.valid_ = false; return c; }
        int minX = std::numeric_limits<int>::max(), minZ = std::numeric_limits<int>::max();
        int maxX = std::numeric_limits<int>::min(), maxZ = std::numeric_limits<int>::min();
        for (const auto& [pos, chunk] : world.chunks()) {
            (void)chunk;
            minX = std::min(minX, pos.x * 16); maxX = std::max(maxX, pos.x * 16 + 15);
            minZ = std::min(minZ, pos.z * 16); maxZ = std::max(maxZ, pos.z * 16 + 15);
        }
        c.bounds_ = {minX, 0, minZ, maxX, kChunkHeight - 1, maxZ};

        auto key = [&](int x, int y, int z) {
            return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(x)) << 42)
                 ^ (static_cast<std::uint64_t>(static_cast<std::uint32_t>(z)) << 21)
                 ^  static_cast<std::uint64_t>(static_cast<std::uint32_t>(y));
        };

        // Flood fill component 0 from the AABB surface.
        std::deque<std::array<std::int32_t,3>> queue;
        auto tryPush = [&](int x, int y, int z) {
            if (x < c.bounds_.minX || x > c.bounds_.maxX || y < 0 || y >= kChunkHeight
                || z < c.bounds_.minZ || z > c.bounds_.maxZ) return;
            if (blocks::opaque(world.getBlock(x, y, z))) return;
            const std::uint64_t k = key(x, y, z);
            if (c.component_.find(k) != c.component_.end()) return;
            c.component_.emplace(k, 0);
            queue.push_back({x, y, z});
        };
        for (int x = c.bounds_.minX; x <= c.bounds_.maxX; ++x)
            for (int z = c.bounds_.minZ; z <= c.bounds_.maxZ; ++z) {
                tryPush(x, 0, z); tryPush(x, kChunkHeight - 1, z);
            }
        for (int y = 0; y < kChunkHeight; ++y) {
            for (int x = c.bounds_.minX; x <= c.bounds_.maxX; ++x) { tryPush(x, y, c.bounds_.minZ); tryPush(x, y, c.bounds_.maxZ); }
            for (int z = c.bounds_.minZ; z <= c.bounds_.maxZ; ++z) { tryPush(c.bounds_.minX, y, z); tryPush(c.bounds_.maxX, y, z); }
        }
        while (!queue.empty()) {
            const auto [x, y, z] = queue.front(); queue.pop_front();
            const int dx[6] = {1,-1,0,0,0,0}, dy[6] = {0,0,1,-1,0,0}, dz[6] = {0,0,0,0,1,-1};
            for (int i = 0; i < 6; ++i) tryPush(x + dx[i], y + dy[i], z + dz[i]);
        }
        // Sealed components: any remaining non-opaque cell not in component 0.
        int nextId = 1;
        for (int y = 0; y < kChunkHeight; ++y) for (int z = c.bounds_.minZ; z <= c.bounds_.maxZ; ++z) for (int x = c.bounds_.minX; x <= c.bounds_.maxX; ++x) {
            if (blocks::opaque(world.getBlock(x, y, z))) continue;
            const std::uint64_t k = key(x, y, z);
            if (c.component_.find(k) != c.component_.end()) continue;
            // New sealed component: BFS with id nextId, but label cells with ids; 0 = reachable remains distinct.
            const int id = nextId++;
            c.component_.emplace(k, id);
            std::deque<std::array<std::int32_t,3>> q2{{x, y, z}};
            while (!q2.empty()) {
                const auto [cx, cy, cz] = q2.front(); q2.pop_front();
                const int dx[6] = {1,-1,0,0,0,0}, dy[6] = {0,0,1,-1,0,0}, dz[6] = {0,0,0,0,1,-1};
                for (int i = 0; i < 6; ++i) {
                    const int nx = cx + dx[i], ny = cy + dy[i], nz = cz + dz[i];
                    if (nx < c.bounds_.minX || nx > c.bounds_.maxX || ny < 0 || ny >= kChunkHeight
                        || nz < c.bounds_.minZ || nz > c.bounds_.maxZ) continue;
                    if (blocks::opaque(world.getBlock(nx, ny, nz))) continue;
                    const std::uint64_t nk = key(nx, ny, nz);
                    if (c.component_.find(nk) != c.component_.end()) continue;
                    c.component_.emplace(nk, id);
                    q2.push_back({nx, ny, nz});
                }
            }
        }
        c.valid_ = true;
        return c;
    }

    bool valid() const { return valid_; }

    // Component of a cell: 0 = reachable/outside/unknown, >0 = sealed component id.
    int componentOf(int x, int y, int z) const {
        const auto it = component_.find(keyOf(x, y, z));
        return it == component_.end() ? 0 : it->second;
    }
    bool sealedAt(int x, int y, int z) const { return componentOf(x, y, z) > 0; }

    // Component the camera is in (0 if camera is in solid/unknown cells).
    int cameraComponent(int x, int y, int z) const { return componentOf(x, y, z); }

    std::size_t sealedCells() const {
        std::size_t n = 0;
        for (const auto& [_, id] : component_) if (id > 0) ++n;
        return n;
    }
    std::size_t componentCount() const {
        int maxId = 0;
        for (const auto& [_, id] : component_) maxId = std::max(maxId, id);
        return static_cast<std::size_t>(maxId);
    }

private:
    static std::uint64_t keyOf(int x, int y, int z) {
        return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(x)) << 42)
             ^ (static_cast<std::uint64_t>(static_cast<std::uint32_t>(z)) << 21)
             ^  static_cast<std::uint64_t>(static_cast<std::uint32_t>(y));
    }
    Bounds bounds_{0, 0, 0, 0, 0, 0};
    std::unordered_map<std::uint64_t, int> component_;
    bool valid_ = true;
};

// No-op culler with the same interface (mesher fast path when cave culling is disabled).
struct NoCaveCuller {
    bool sealedAt(int, int, int) const { return false; }
    int cameraComponent(int, int, int) const { return 0; }
    int componentOf(int, int, int) const { return 0; }
};

} // namespace vc
