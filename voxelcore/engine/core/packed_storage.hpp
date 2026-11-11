// PROJECT VOXELCORE — bit-packed integer array (PalettedContainer-style storage).
// Values of `bits` bits each, packed densely into 64-bit words, 4096 entries by default.
// Layout matches the intent of Horizon's PackedStorage (horizon-core/src/storage.rs) and
// Minecraft's DataLayer: entries never straddle a 64-bit word boundary when bits divides
// the word evenly; for simplicity and speed we use word-per-entry packing only when bits
// is 8/16, and a bitstream otherwise.
#pragma once

#include <cstdint>
#include <cstddef>
#include <vector>
#include <stdexcept>
#include <algorithm>
#include <limits>

namespace vc {

class PackedArray {
public:
    PackedArray() = default;
    PackedArray(std::uint8_t bits, std::size_t entries) { init(bits, entries); }

    void init(std::uint8_t bits, std::size_t entries) {
        if (bits > 64) throw std::invalid_argument("PackedArray: bits > 64");
        bits_ = bits;
        entries_ = entries;
        words_.assign(wordCount(bits, entries), 0);
    }

    static constexpr std::size_t wordCount(std::uint8_t bits, std::size_t entries) {
        if (bits == 0) return 0;
        return (entries * bits + 63) / 64;
    }

    std::uint8_t bits() const { return bits_; }
    std::size_t entries() const { return entries_; }
    std::size_t words() const { return words_.size(); }
    std::size_t bytes() const { return words_.size() * sizeof(std::uint64_t); }

    std::uint64_t get(std::size_t i) const {
        if (bits_ == 0) return 0;
        if (i >= entries_) throw std::out_of_range("PackedArray::get");
        const std::uint64_t bitPos = static_cast<std::uint64_t>(i) * bits_;
        const std::size_t word = static_cast<std::size_t>(bitPos >> 6);
        const std::uint32_t offset = static_cast<std::uint32_t>(bitPos & 63);
        const std::uint64_t mask = (bits_ == 64) ? ~std::uint64_t{0} : ((std::uint64_t{1} << bits_) - 1);
        const std::uint64_t lo = words_[word] >> offset;
        if (offset + bits_ <= 64) return lo & mask;
        const std::uint64_t hi = words_[word + 1] << (64 - offset);
        return (lo | hi) & mask;
    }

    void set(std::size_t i, std::uint64_t value) {
        if (bits_ == 0) {
            if (value != 0) throw std::invalid_argument("PackedArray: nonzero value in 0-bit array");
            return;
        }
        if (i >= entries_) throw std::out_of_range("PackedArray::set");
        const std::uint64_t mask = (bits_ == 64) ? ~std::uint64_t{0} : ((std::uint64_t{1} << bits_) - 1);
        value &= mask;
        const std::uint64_t bitPos = static_cast<std::uint64_t>(i) * bits_;
        const std::size_t word = static_cast<std::size_t>(bitPos >> 6);
        const std::uint32_t offset = static_cast<std::uint32_t>(bitPos & 63);
        const std::uint64_t clear = ~(mask << offset);
        words_[word] = (words_[word] & clear) | (value << offset);
        if (offset + bits_ > 64) {
            const std::uint32_t spill = static_cast<std::uint32_t>(offset + bits_ - 64);
            const std::uint64_t himask = (std::uint64_t{1} << spill) - 1;
            words_[word + 1] = (words_[word + 1] & ~himask) | (value >> (bits_ - spill));
        }
    }

    const std::vector<std::uint64_t>& rawWords() const { return words_; }
    std::vector<std::uint64_t>& rawWordsMutable() { return words_; }

private:
    std::uint8_t bits_ = 0;
    std::size_t entries_ = 0;
    std::vector<std::uint64_t> words_;
};

} // namespace vc
