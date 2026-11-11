// PROJECT VOXELCORE — cached block reader for hot paths (mesher, physics queries).
// Caches the last-hit chunk; single-threaded use (create one per worker/mesh task).
#pragma once

#include "world.hpp"

namespace vc {

struct CachedBlockReader {
    const World& world;
    explicit CachedBlockReader(const World& w) : world(w) {}

    BlockId operator()(int x, int y, int z) const {
        if (y < 0 || y >= kChunkHeight) return blocks::Air;
        const ChunkPos p{x >> 4, z >> 4};
        if (!valid_ || last_ != p) {
            lastChunk_ = world.chunkAt(p);
            last_ = p;
            valid_ = true;
        }
        if (!lastChunk_) return blocks::Air;
        return lastChunk_->getBlock(x & 15, y, z & 15);
    }

private:
    mutable const Chunk* lastChunk_ = nullptr;
    mutable ChunkPos last_{};
    mutable bool valid_ = false;
};

} // namespace vc
