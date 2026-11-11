// PROJECT VOXELCORE — Anvil region file (.mca) read/write.
// Layout (public format documentation, wiki.vg/Anvil_file_format):
//   bytes 0..4095: 1024 x 4-byte big-endian sector locations (offset<<8 | sectorCount)
//   bytes 4096..8191: 1024 x 4-byte big-endian Unix timestamps
//   then chunk records: 4-byte BE length, 1-byte compression (1 = zlib RFC1950), payload.
// Sectors are 4096 bytes. Chunk index: (x&31) + (z&31)*32.
// This implementation buffers chunks in memory and rewrites the file on flush().
// Correct and simple; O(file size) per save. Incremental sector allocation is a stage-13 item.
#pragma once

#include "zlib.hpp"
#include <cstdint>
#include <cstring>
#include <fstream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace vc::anvil {

constexpr std::size_t kSectorSize = 4096;
constexpr std::uint8_t kCompressionZlib = 1;
constexpr std::uint8_t kCompressionNone = 3;

class RegionFile {
public:
    // Opens or creates the region file; existing chunks are indexed lazily on read.
    RegionFile(const std::string& path, bool createIfMissing = true) : path_(path) {
        std::ifstream in(path, std::ios::binary);
        if (in) {
            in.seekg(0, std::ios::end);
            const std::streamoff size = in.tellg();
            if (size >= static_cast<std::streamoff>(2 * kSectorSize)) {
                in.seekg(0, std::ios::beg);
                raw_.resize(static_cast<std::size_t>(size));
                in.read(reinterpret_cast<char*>(raw_.data()), size);
            }
        } else if (!createIfMissing) {
            throw std::runtime_error("region: cannot open " + path);
        }
    }

    bool hasChunk(int localX, int localZ) const {
        const std::size_t idx = index(localX, localZ);
        if (dirty_.count(idx)) return true;
        if (raw_.empty()) return false;
        const std::uint32_t loc = readU32BE(raw_.data() + idx * 4);
        return (loc >> 8) != 0;
    }

    // Reads the (still compressed) chunk payload. Compression byte is returned via `compression`.
    std::vector<std::uint8_t> readChunk(int localX, int localZ, std::uint8_t& compression) const {
        const std::size_t idx = index(localX, localZ);
        if (const auto it = dirty_.find(idx); it != dirty_.end()) {
            compression = it->second.first;
            return it->second.second;
        }
        if (raw_.empty()) throw std::runtime_error("region: chunk absent");
        const std::uint32_t loc = readU32BE(raw_.data() + idx * 4);
        const std::uint32_t sectorOffset = loc >> 8;
        const std::uint32_t sectorCount = loc & 0xFF;
        if (sectorOffset == 0 || sectorCount == 0) throw std::runtime_error("region: chunk absent");
        const std::size_t base = static_cast<std::size_t>(sectorOffset) * kSectorSize;
        if (base + 5 > raw_.size()) throw std::runtime_error("region: corrupt offset");
        const std::uint32_t length = readU32BE(raw_.data() + base);
        if (length < 1 || base + 4 + length > raw_.size()) throw std::runtime_error("region: corrupt length");
        compression = raw_[base + 4];
        return std::vector<std::uint8_t>(raw_.begin() + base + 5, raw_.begin() + base + 4 + length);
    }

    // Stores a compressed (or raw) chunk payload; file rewritten on flush().
    void writeChunk(int localX, int localZ, std::uint8_t compression, std::vector<std::uint8_t> payload) {
        const std::size_t idx = index(localX, localZ);
        dirty_[idx] = {compression, std::move(payload)};
    }

    void flush(std::uint32_t timestamp = 1700000000u) {
        std::vector<char> handled(1024, 0);
        std::vector<std::uint8_t> out(2 * kSectorSize, 0);
        std::uint32_t sector = 2;
        auto emit = [&](std::size_t idx, std::uint8_t comp, const std::vector<std::uint8_t>& payload) {
            const std::uint32_t recordLen = static_cast<std::uint32_t>(payload.size()) + 1;
            const std::uint32_t sectorCount = (recordLen + 4 + kSectorSize - 1) / kSectorSize;
            const std::size_t base = static_cast<std::size_t>(sector) * kSectorSize;
            out.resize(base + sectorCount * kSectorSize, 0);
            const std::uint32_t beLen = recordLen;
            out[base + 0] = static_cast<std::uint8_t>(beLen >> 24);
            out[base + 1] = static_cast<std::uint8_t>(beLen >> 16);
            out[base + 2] = static_cast<std::uint8_t>(beLen >> 8);
            out[base + 3] = static_cast<std::uint8_t>(beLen & 0xFF);
            out[base + 4] = comp;
            std::memcpy(out.data() + base + 5, payload.data(), payload.size());
            const std::uint32_t loc = (sector << 8) | sectorCount;
            out[idx * 4 + 0] = static_cast<std::uint8_t>(loc >> 24);
            out[idx * 4 + 1] = static_cast<std::uint8_t>(loc >> 16);
            out[idx * 4 + 2] = static_cast<std::uint8_t>(loc >> 8);
            out[idx * 4 + 3] = static_cast<std::uint8_t>(loc & 0xFF);
            for (int b = 0; b < 4; ++b) out[4096 + idx * 4 + b] = static_cast<std::uint8_t>((timestamp >> (24 - 8 * b)) & 0xFF);
            sector += sectorCount;
        };
        for (const auto& [idx, p] : dirty_) { emit(idx, p.first, p.second); handled[idx] = 1; }
        if (!raw_.empty()) {
            for (std::size_t idx = 0; idx < 1024; ++idx) {
                if (handled[idx]) continue;
                const std::uint32_t loc = readU32BE(raw_.data() + idx * 4);
                const std::uint32_t sectorOffset = loc >> 8, sectorCount = loc & 0xFF;
                if (sectorOffset == 0 || sectorCount == 0) continue;
                const std::size_t base = static_cast<std::size_t>(sectorOffset) * kSectorSize;
                const std::uint32_t length = readU32BE(raw_.data() + base);
                const std::uint8_t comp = raw_[base + 4];
                const std::vector<std::uint8_t> payload(raw_.begin() + base + 5, raw_.begin() + base + 4 + length);
                emit(idx, comp, payload);
            }
        }
        std::ofstream f(path_, std::ios::binary | std::ios::trunc);
        f.write(reinterpret_cast<const char*>(out.data()), static_cast<std::streamsize>(out.size()));
        f.close();
        raw_ = std::move(out);
        dirty_.clear();
    }

private:
    static std::size_t index(int localX, int localZ) {
        return static_cast<std::size_t>((localZ & 31) * 32 + (localX & 31));
    }
    static std::uint32_t readU32BE(const std::uint8_t* p) {
        return (static_cast<std::uint32_t>(p[0]) << 24) | (static_cast<std::uint32_t>(p[1]) << 16)
             | (static_cast<std::uint32_t>(p[2]) << 8)  |  static_cast<std::uint32_t>(p[3]);
    }

    std::string path_;
    std::vector<std::uint8_t> raw_;                              // original file content (if any)
    std::map<std::size_t, std::pair<std::uint8_t, std::vector<std::uint8_t>>> dirty_;
};

} // namespace vc::anvil
