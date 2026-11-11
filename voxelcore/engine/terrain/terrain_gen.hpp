// PROJECT VOXELCORE — deterministic heightmap terrain generator.
// Base height = fBm(continentalness) + fBm(detail); sea level fills water;
// stone under dirt under grass; sand at the shoreline; trees scattered by hash.
// Deterministic for a given seed across platforms (integer hashing only).
#pragma once

#include "noise.hpp"
#include "../chunks/chunk.hpp"
#include "../chunks/block_ids.hpp"
#include "../world/world.hpp"
#include <cstdint>
#include <cmath>

namespace vc {

struct TerrainConfig {
    std::uint64_t seed = 1337;
    int seaLevel = 24;          // y of water surface
    double continentScale = 1.0 / 384.0;
    double hillScale = 1.0 / 96.0;
    double baseHeight = 30.0;
    double continentAmp = 14.0;
    double hillAmp = 7.0;
    double detailAmp = 2.5;
    double treeDensity = 0.0045; // per-column probability-ish (hash threshold)
    bool trees = true;
};

class TerrainGenerator {
public:
    explicit TerrainGenerator(TerrainConfig cfg) : cfg_(cfg), continent_(cfg.seed ^ 0xC0FFEE), detail_(cfg.seed ^ 0xBADC0DE) {}

    // Surface height (highest solid block y) at world (x, z). Deterministic.
    int surfaceHeight(int x, int z) const {
        const double cont = continent_.fbm2D(x * cfg_.continentScale, z * cfg_.continentScale, 4);
        const double hills = detail_.fbm2D(x * cfg_.hillScale, z * cfg_.hillScale, 4);
        const double ridge = detail_.value2D(x * 0.008 + 91.7, z * 0.008 - 33.1);
        double h = cfg_.baseHeight + cont * cfg_.continentAmp + hills * cfg_.hillAmp + ridge * cfg_.detailAmp;
        const int hi = static_cast<int>(std::floor(h));
        return hi < 1 ? 1 : (hi > kChunkHeight - 2 ? kChunkHeight - 2 : hi);
    }

    void generate(Chunk& chunk) const {
        const ChunkPos cp = chunk.pos();
        for (int z = 0; z < 16; ++z) for (int x = 0; x < 16; ++x) {
            const int wx = cp.x * 16 + x, wz = cp.z * 16 + z;
            const int surf = surfaceHeight(wx, wz);
            const bool beach = surf <= cfg_.seaLevel + 1;
            for (int y = 0; y <= surf; ++y) {
                BlockId b = blocks::Stone;
                if (y == 0) b = blocks::Bedrock;
                else if (y == surf) b = beach ? blocks::Sand : (surf > cfg_.seaLevel + 18 ? blocks::Snow : blocks::Grass);
                else if (y >= surf - 3) b = beach ? blocks::Sand : blocks::Dirt;
                chunk.setBlock(x, y, z, b);
            }
            for (int y = surf + 1; y <= cfg_.seaLevel; ++y) chunk.setBlock(x, y, z, blocks::Water);
            if (cfg_.trees && surf > cfg_.seaLevel && !beach && surf <= cfg_.seaLevel + 16) {
                if (treeAt(wx, wz)) plantTree(chunk, x, surf + 1, z);
            }
        }
        chunk.recomputeHeightMap();
    }

private:
    bool treeAt(int wx, int wz) const {
        // Stable per-column hash → tree presence.
        std::uint64_t h = static_cast<std::uint64_t>(static_cast<std::uint32_t>(wx)) * 0x9E3779B97F4A7C15ull
                        ^ static_cast<std::uint64_t>(static_cast<std::uint32_t>(wz)) * 0xC2B2AE3D27D4EB4Full
                        ^ cfg_.seed * 0x165667B19E3779F9ull;
        h ^= h >> 33; h *= 0xFF51AFD7ED558CCDull; h ^= h >> 33;
        // ~treeDensity of columns.
        return (h >> 40) < static_cast<std::uint64_t>(cfg_.treeDensity * 16777216.0);
    }

    void plantTree(Chunk& chunk, int x, int y, int z) const {
        const int trunk = 4 + static_cast<int>(hashLocal(x, chunk.pos().x, chunk.pos().z) & 1);
        for (int i = 0; i < trunk; ++i) chunk.setBlock(x, y + i, z, blocks::Log);
        const int top = y + trunk;
        for (int dy = -2; dy <= 0; ++dy) {
            const int r = (dy == 0) ? 1 : 2;
            for (int dz = -r; dz <= r; ++dz) for (int dx = -r; dx <= r; ++dx) {
                if (std::abs(dx) == r && std::abs(dz) == r) continue;
                const int lx = x + dx, ly = top + dy, lz = z + dz;
                // Only fill inside the chunk column; cross-chunk leaves are skipped by design (documented simplification).
                if (chunk.getBlock(lx, ly, lz) == blocks::Air) chunk.setBlock(lx, ly, lz, blocks::Leaves);
            }
        }
        chunk.setBlock(x, top + 1, z, blocks::Leaves);
    }

    static std::uint64_t hashLocal(int a, int b, int c) {
        std::uint64_t h = static_cast<std::uint64_t>(static_cast<std::uint32_t>(a)) * 0x9E3779B97F4A7C15ull
                        ^ static_cast<std::uint64_t>(static_cast<std::uint32_t>(b)) * 0xC2B2AE3D27D4EB4Full
                        ^ static_cast<std::uint64_t>(static_cast<std::uint32_t>(c)) * 0x165667B19E3779F9ull;
        h ^= h >> 33; h *= 0xFF51AFD7ED558CCDull; h ^= h >> 33;
        return h;
    }

    TerrainConfig cfg_;
    Noise continent_, detail_;
};

} // namespace vc
