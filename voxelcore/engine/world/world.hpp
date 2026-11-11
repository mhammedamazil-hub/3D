// PROJECT VOXELCORE — sparse world container for chunk columns.
// Flat hash map of chunks; thread-safe only under external synchronization (meshing reads
// while generation writes different chunks is allowed by design; same-chunk races are not).
#pragma once

#include "../chunks/chunk.hpp"
#include <unordered_map>
#include <memory>
#include <mutex>

namespace vc {

class World {
public:
    // Returns existing chunk or nullptr.
    Chunk* chunkAt(ChunkPos p) {
        const auto it = chunks_.find(p);
        return it == chunks_.end() ? nullptr : it->second.get();
    }
    const Chunk* chunkAt(ChunkPos p) const {
        const auto it = chunks_.find(p);
        return it == chunks_.end() ? nullptr : it->second.get();
    }
    Chunk& getOrCreate(ChunkPos p) {
        auto it = chunks_.find(p);
        if (it == chunks_.end()) it = chunks_.emplace(p, std::make_unique<Chunk>(p)).first;
        return *it->second;
    }
    bool remove(ChunkPos p) { return chunks_.erase(p) > 0; }
    std::size_t chunkCount() const { return chunks_.size(); }
    std::size_t approxBytes() const {
        std::size_t t = 0;
        for (const auto& [_, c] : chunks_) t += c->approxBytes();
        return t;
    }
    const auto& chunks() const { return chunks_; }

    BlockId getBlock(int x, int y, int z) const {
        if (y < 0 || y >= kChunkHeight) return blocks::Air;
        const int cx = x >> 4, cz = z >> 4;
        const Chunk* c = chunkAt({cx, cz});
        if (!c) return blocks::Air;
        return c->getBlock(x & 15, y, z & 15);
    }
    void setBlock(int x, int y, int z, BlockId b) {
        if (y < 0 || y >= kChunkHeight) return;
        Chunk& c = getOrCreate({x >> 4, z >> 4});
        c.setBlock(x & 15, y, z & 15, b);
    }

private:
    std::unordered_map<ChunkPos, std::unique_ptr<Chunk>, ChunkPosHash> chunks_;
};

} // namespace vc
