// PROJECT VOXELCORE — distant-terrain LOD: baked heightfield column + LOD mesh.
// Reduces a chunk (or region) to coarse columns with the highest non-air block, median
// material below, and emits a simplified terrain mesh at 1/2^level resolution.
// Inspired by clipmaps/Distant Horizons; full voxel sim is never required for far LOD.
#pragma once

#include "../chunks/chunk.hpp"
#include "../chunks/block_ids.hpp"
#include "../world/world.hpp"
#include <vector>
#include <cstdint>
#include <cmath>

namespace vc {

struct LodColumn {
    std::int16_t height = 0;   // y of the highest solid block + 1 (surface)
    BlockId surface = blocks::Grass;
    BlockId subsurface = blocks::Dirt;
};

struct LodMesh {
    std::vector<float> positions; // xyz triples
    std::vector<std::uint32_t> indices;
    std::uint64_t cells = 0;
};

class HeightfieldLod {
public:
    // Bake a region of `regionChunks` x `regionChunks` chunks into lodLevel-coarsened
    // columns. Level 0 = 1 m cells, 1 = 2 m, 2 = 4 m, ...
    static std::vector<LodColumn> bake(const World& world, int chunkX, int chunkZ, int level) {
        const int step = 1 << level;
        const int region = 16 * step;              // world units covered per baked tile
        const int cells = 16;                       // cells per side at any level
        std::vector<LodColumn> out(static_cast<std::size_t>(cells) * cells);
        for (int cz = 0; cz < cells; ++cz) for (int cx = 0; cx < cells; ++cx) {
            LodColumn& col = out[static_cast<std::size_t>(cz) * cells + cx];
            const int bx = chunkX * region + cx * step, bz = chunkZ * region + cz * step;
            std::int16_t best = 0;
            for (int dz = 0; dz < step; ++dz) for (int dx = 0; dx < step; ++dx) {
                // Highest non-air at this sample; sample the chunk heightmap where possible.
                for (int y = kChunkHeight - 1; y >= 0; --y) {
                    if (world.getBlock(bx + dx, y, bz + dz) != blocks::Air) {
                        if (y + 1 > best) {
                            best = static_cast<std::int16_t>(y + 1);
                            col.surface = world.getBlock(bx + dx, y, bz + dz);
                            col.subsurface = (y > 0) ? world.getBlock(bx + dx, y - 1, bz + dz) : col.surface;
                        }
                        break;
                    }
                }
            }
            col.height = best;
        }
        return out;
    }

    // Emit a triangulated grid mesh from a baked tile. Positions absolute (origin at tile origin).
    static LodMesh mesh(const std::vector<LodColumn>& tile, int originX, int originZ, int level) {
        const int step = 1 << level;
        const int cells = 16;
        LodMesh m;
        m.cells = static_cast<std::uint64_t>(cells) * cells;
        m.positions.reserve(static_cast<std::size_t>(cells + 1) * (cells + 1) * 3);
        for (int z = 0; z <= cells; ++z) for (int x = 0; x <= cells; ++x) {
            // Vertex height: average of adjacent baked cell heights (smooth LOD surface).
            double sum = 0; int n = 0;
            for (int dz = -1; dz <= 0; ++dz) for (int dx = -1; dx <= 0; ++dx) {
                const int cx = x + dx, cz = z + dz;
                if (cx >= 0 && cx < cells && cz >= 0 && cz < cells) { sum += tile[static_cast<std::size_t>(cz) * cells + cx].height; ++n; }
            }
            const float h = n ? static_cast<float>(sum / n) : 0.0f;
            m.positions.push_back(static_cast<float>(originX + x * step));
            m.positions.push_back(h);
            m.positions.push_back(static_cast<float>(originZ + z * step));
        }
        for (int z = 0; z < cells; ++z) for (int x = 0; x < cells; ++x) {
            const std::uint32_t i00 = static_cast<std::uint32_t>(z * (cells + 1) + x);
            const std::uint32_t i10 = i00 + 1, i01 = i00 + (cells + 1), i11 = i01 + 1;
            m.indices.insert(m.indices.end(), {i00, i01, i10, i10, i01, i11});
        }
        return m;
    }
};

} // namespace vc
