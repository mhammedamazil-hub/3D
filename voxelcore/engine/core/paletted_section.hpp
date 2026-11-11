// PROJECT VOXELCORE — palette-compressed 16^3 voxel section.
// Mirrors Minecraft's PalettedContainer and Horizon's chunk.rs storage, tuned for C++:
//  - uniform sections cost 0 bits of storage,
//  - bits-per-entry grows on demand (4 -> 8 -> ... -> 16),
//  - values above the current palette grow it; unused palette entries are never re-compacted
//    automatically (call trim() if desired).
#pragma once

#include "packed_storage.hpp"
#include "types.hpp"
#include <vector>
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <unordered_map>

namespace vc {

class PalettedSection {
public:
    PalettedSection() { fill(kAir); }

    void fill(BlockId block) {
        palette_.clear();
        palette_.push_back(block);
        index_.clear();
        index_.emplace(block, 0);
        storage_ = PackedArray(); // 0 bits: uniform
        nonUniform_ = false;
    }

    bool isUniform() const { return !nonUniform_; }
    BlockId uniformValue() const { return palette_.empty() ? kAir : palette_.front(); }

    BlockId get(std::size_t i) const {
        if (i >= kSectionVolume) throw std::out_of_range("PalettedSection::get");
        if (!nonUniform_) return palette_.front();
        return palette_[static_cast<std::size_t>(storage_.get(i))];
    }
    BlockId get(std::size_t x, std::size_t y, std::size_t z) const { return get(sectionIndex(x, y, z)); }

    void set(std::size_t i, BlockId block) {
        if (i >= kSectionVolume) throw std::out_of_range("PalettedSection::set");
        if (!nonUniform_) {
            if (palette_.front() == block) return;
            // Go non-uniform: allocate storage replicating the uniform value.
            const BlockId first = palette_.front();
            palette_.clear();
            index_.clear();
            palette_.push_back(first); index_.emplace(first, 0);
            palette_.push_back(block); index_.emplace(block, 1);
            storage_.init(bitsFor(palette_.size()), kSectionVolume);
            // storage_ is zero-initialised => every cell reads palette_[0] == first. Correct.
            nonUniform_ = true;
            if (palette_.size() > 1) storage_.set(i, 1);
            return;
        }
        std::size_t idx = paletteIndex(block);
        if (idx == npos) {
            idx = palette_.size();
            palette_.push_back(block);
            index_.emplace(block, idx);
            const std::uint8_t need = bitsFor(palette_.size());
            if (need > storage_.bits()) growStorage(need);
        }
        storage_.set(i, idx);
    }
    void set(std::size_t x, std::size_t y, std::size_t z, BlockId block) { set(sectionIndex(x, y, z), block); }

    std::size_t paletteSize() const { return palette_.size(); }
    std::size_t storageBytes() const { return storage_.bytes(); }
    std::size_t approxBytes() const { return storage_.bytes() + palette_.size() * sizeof(BlockId); }
    const std::vector<BlockId>& palette() const { return palette_; }

    // Recount the used palette entries and rebuild a tight palette (shrinks bits).
    void trim() {
        if (!nonUniform_) return;
        std::vector<char> used(palette_.size(), 0);
        for (std::size_t i = 0; i < kSectionVolume; ++i) used[static_cast<std::size_t>(storage_.get(i))] = 1;
        std::vector<BlockId> remap(palette_.size(), 0);
        std::vector<BlockId> tight;
        tight.reserve(palette_.size());
        for (std::size_t i = 0; i < palette_.size(); ++i) {
            if (used[i]) { remap[i] = static_cast<BlockId>(tight.size()); tight.push_back(palette_[i]); }
        }
        if (tight.size() <= 1) { const BlockId v = tight.empty() ? kAir : tight.front(); fill(v); return; }
        PackedArray fresh(bitsFor(tight.size()), kSectionVolume);
        for (std::size_t i = 0; i < kSectionVolume; ++i) fresh.set(i, remap[static_cast<std::size_t>(storage_.get(i))]);
        palette_.swap(tight);
        index_.clear();
        for (std::size_t i = 0; i < palette_.size(); ++i) index_.emplace(palette_[i], i);
        storage_ = std::move(fresh);
    }

private:
    static constexpr std::size_t npos = static_cast<std::size_t>(-1);
    static std::uint8_t bitsFor(std::size_t paletteLen) {
        std::uint8_t bits = 1;
        while ((std::size_t{1} << bits) < paletteLen) ++bits;
        return std::max<std::uint8_t>(bits, 1);
    }
    std::size_t paletteIndex(BlockId block) const {
        const auto it = index_.find(block);
        return it == index_.end() ? npos : it->second;
    }
    void growStorage(std::uint8_t newBits) {
        PackedArray grown(newBits, kSectionVolume);
        for (std::size_t i = 0; i < kSectionVolume; ++i) grown.set(i, storage_.get(i));
        storage_ = std::move(grown);
    }

    std::vector<BlockId> palette_;
    std::unordered_map<BlockId, std::size_t> index_;
    PackedArray storage_;
    bool nonUniform_ = false;
};

} // namespace vc
