// PROJECT VOXELCORE — linear (bump) arena allocator.
// For frame-scoped or batch-scoped scratch: O(1) allocation, O(1) bulk release,
// no per-object bookkeeping. Not suitable for individual frees.
#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>
#include <stdexcept>

namespace vc {

class Arena {
public:
    explicit Arena(std::size_t blockBytes = 1 << 20) : blockBytes_(blockBytes) { allocateBlock(blockBytes_); }

    Arena(const Arena&) = delete;
    Arena& operator=(const Arena&) = delete;

    void* allocate(std::size_t bytes, std::size_t align = alignof(std::max_align_t)) {
        if (bytes == 0) bytes = 1;
        std::size_t off = (used_ + (align - 1)) & ~(align - 1);
        if (off + bytes > blocks_.back().size()) {
            allocateBlock(std::max(bytes + align, blockBytes_));
            off = 0;
        }
        used_ = off + bytes;
        totalAllocated_ += bytes;
        return blocks_.back().data() + off;
    }

    template <typename T, typename... Args> T* create(Args&&... args) {
        void* p = allocate(sizeof(T), alignof(T));
        return new (p) T(static_cast<Args&&>(args)...);
    }

    // Releases every allocation made so far; keeps one block for reuse.
    void reset() noexcept {
        // Keep the first block for reuse; drop the rest.
        if (blocks_.size() > 1) blocks_.erase(blocks_.begin() + 1, blocks_.end());
        if (blocks_.empty()) allocateBlock(blockBytes_);
        used_ = 0;
    }

    std::size_t bytesUsed() const noexcept {
        std::size_t sum = 0;
        for (std::size_t i = 0; i + 1 < blocks_.size(); ++i) sum += blocks_[i].size();
        return sum + used_;
    }
    std::size_t bytesAllocated() const noexcept { return totalAllocated_; }
    std::size_t blockCount() const noexcept { return blocks_.size(); }

private:
    void allocateBlock(std::size_t bytes) {
        blocks_.emplace_back(bytes);
        used_ = 0;
    }
    struct Block {
        explicit Block(std::size_t n) : data_(std::make_unique<std::byte[]>(n)), size_(n) {}
        Block(Block&&) = default;
        Block& operator=(Block&&) = default;
        std::byte* data() { return data_.get(); }
        std::size_t size() const { return size_; }
    private:
        std::unique_ptr<std::byte[]> data_;
        std::size_t size_;
    };
    std::size_t blockBytes_;
    std::vector<Block> blocks_;
    std::size_t used_ = 0;
    std::size_t totalAllocated_ = 0;
};

} // namespace vc
