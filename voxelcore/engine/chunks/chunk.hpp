// PROJECT VOXELCORE — chunk column: kChunkSections palette-compressed sections + heightmap.
#pragma once

#include "../core/paletted_section.hpp"
#include "../core/types.hpp"
#include "block_ids.hpp"
#include <array>
#include <cstdint>
#include <vector>

namespace vc {

class Chunk {
public:
    explicit Chunk(ChunkPos pos) : pos_(pos) {}

    ChunkPos pos() const { return pos_; }

    BlockId getBlock(int x, int y, int z) const {
        if (x < 0 || x >= 16 || z < 0 || z >= 16 || y < 0 || y >= kChunkHeight) return blocks::Air;
        const std::size_t s = static_cast<std::size_t>(y) / kSectionSize;
        const std::size_t ly = static_cast<std::size_t>(y) % kSectionSize;
        return sections_[s].get(static_cast<std::size_t>(x), ly, static_cast<std::size_t>(z));
    }
    void setBlock(int x, int y, int z, BlockId b) {
        if (x < 0 || x >= 16 || z < 0 || z >= 16 || y < 0 || y >= kChunkHeight) return;
        const std::size_t s = static_cast<std::size_t>(y) / kSectionSize;
        const std::size_t ly = static_cast<std::size_t>(y) % kSectionSize;
        sections_[s].set(static_cast<std::size_t>(x), ly, static_cast<std::size_t>(z), b);
        if (b != blocks::Air) { if (y > heightMap_[z * 16 + x]) heightMap_[z * 16 + x] = static_cast<std::int16_t>(y); }
    }

    // Authoritative heightmap rebuild (O(4096)): use after bulk writes.
    void recomputeHeightMap() {
        heightMap_.fill(0);
        for (int z = 0; z < 16; ++z) for (int x = 0; x < 16; ++x) {
            for (int y = kChunkHeight - 1; y >= 0; --y) {
                if (getBlock(x, y, z) != blocks::Air) { heightMap_[z * 16 + x] = static_cast<std::int16_t>(y); break; }
            }
        }
    }

    PalettedSection& section(std::size_t i) { return sections_[i]; }
    const PalettedSection& section(std::size_t i) const { return sections_[i]; }

    std::int16_t heightAt(int x, int z) const { return heightMap_[z * 16 + x]; }
    std::size_t approxBytes() const {
        std::size_t t = 0;
        for (const auto& s : sections_) t += s.approxBytes();
        return t + heightMap_.size() * sizeof(std::int16_t);
    }

private:
    ChunkPos pos_{};
    std::array<PalettedSection, kChunkSections> sections_;
    std::array<std::int16_t, 256> heightMap_{}; // highest non-air y+1, 0 if all air; refined on setBlock
};

} // namespace vc
