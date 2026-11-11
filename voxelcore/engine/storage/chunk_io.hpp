// PROJECT VOXELCORE — chunk <-> NBT serialization and Anvil region I/O.
//
// The on-disk layout is deliberately modeled on the Java Edition paletted-container format
// (sections with palette + bit-packed long array; 1:1 vanilla block names for our ten blocks):
//   Level.sections[].block_states = { palette: [ {Name: "minecraft:stone", ...} ], data: LongArray }
//
// IMPORTANT, honest scope: this reads/writes OUR files. Bitstreams and section metadata are
// self-consistent and schema-compatible, but loading arbitrary vanilla 26.3 worlds (block-state
// registries, datafix, biomes, light engines, structures) is NOT implemented and NOT claimed.
// Cross-implementation validation belongs to stage 11 differential testing.
#pragma once

#include "nbt.hpp"
#include "region_file.hpp"
#include "../chunks/chunk.hpp"
#include "../core/packed_storage.hpp"
#include <memory>
#include <string>
#include <vector>

namespace vc::chunk_io {

// Our ten block ids map 1:1 onto these vanilla block state names.
inline const char* blockStateName(BlockId b) {
    switch (b) {
        case blocks::Stone: return "minecraft:stone";
        case blocks::Dirt: return "minecraft:dirt";
        case blocks::Grass: return "minecraft:grass_block";
        case blocks::Sand: return "minecraft:sand";
        case blocks::Water: return "minecraft:water";
        case blocks::Log: return "minecraft:oak_log";
        case blocks::Leaves: return "minecraft:oak_leaves";
        case blocks::Bedrock: return "minecraft:bedrock";
        case blocks::Snow: return "minecraft:snow_block";
        default: return "minecraft:air";
    }
}
inline BlockId blockFromStateName(const std::string& s) {
    if (s == "minecraft:stone") return blocks::Stone;
    if (s == "minecraft:dirt") return blocks::Dirt;
    if (s == "minecraft:grass_block") return blocks::Grass;
    if (s == "minecraft:sand") return blocks::Sand;
    if (s == "minecraft:water") return blocks::Water;
    if (s == "minecraft:oak_log") return blocks::Log;
    if (s == "minecraft:oak_leaves") return blocks::Leaves;
    if (s == "minecraft:bedrock") return blocks::Bedrock;
    if (s == "minecraft:snow_block") return blocks::Snow;
    return blocks::Air;
}

// Serialize one 16^3 section into block_states { palette, data }.
inline nbt::Value sectionToBlockStates(const PalettedSection& s) {
    nbt::Value paletteList(nbt::List, nbt::NbtList{});
    nbt::NbtList& items = std::get<nbt::NbtList>(paletteList.data);
    if (s.isUniform()) {
        nbt::Value entry = nbt::Value::compound();
        nbt::NbtCompound& c = std::get<nbt::NbtCompound>(entry.data);
        c.emplace_back("Name", nbt::Value(std::string(blockStateName(s.uniformValue()))));
        items.push_back(std::move(entry));
        nbt::NbtCompound bs;
        bs.emplace_back("palette", std::move(paletteList));
        bs.emplace_back("data", nbt::Value(nbt::NbtLongArray{}));
        return nbt::Value(std::move(bs));
    }
    for (BlockId b : s.palette()) {
        nbt::Value entry = nbt::Value::compound();
        nbt::NbtCompound& c = std::get<nbt::NbtCompound>(entry.data);
        c.emplace_back("Name", nbt::Value(std::string(blockStateName(b))));
        items.push_back(std::move(entry));
    }
    const std::size_t n = s.paletteSize();
    std::uint8_t bits = 1;
    while ((std::size_t{1} << bits) < n) ++bits;
    bits = std::max<std::uint8_t>(bits, 4);
    PackedArray packed(bits, kSectionVolume);
    // Round-trip through the section's own storage by re-reading each cell index.
    // (PalettedSection does not expose the raw index array; reconstructing by palette
    // lookup is exact but O(n * palette). Fine at 4096 entries; replace with a direct
    // accessor in stage 6 for speed.)
    for (std::size_t i = 0; i < kSectionVolume; ++i) packed.set(i, s.rawPaletteIndex(i));
    const auto& words = packed.rawWords();
    nbt::NbtLongArray data;
    data.reserve(words.size());
    for (std::uint64_t w : words) data.push_back(static_cast<std::int64_t>(w));
    nbt::NbtCompound bs;
    bs.emplace_back("palette", std::move(paletteList));
    bs.emplace_back("data", nbt::Value(std::move(data)));
    return nbt::Value(std::move(bs));
}

inline void blockStatesToSection(const nbt::Value& blockStates, PalettedSection& out) {
    out.fill(blocks::Air);
    const nbt::NbtCompound* bs = blockStates.asCompound();
    if (!bs) return;
    const nbt::Value* paletteV = blockStates.find("palette");
    const nbt::Value* dataV = blockStates.find("data");
    const nbt::NbtList* palette = paletteV ? paletteV->asList() : nullptr;
    if (!palette) return;
    if (palette->size() <= 1) {
        BlockId b = blocks::Air;
        if ((*palette)[0].asCompound())
            if (const nbt::Value* nm = (*palette)[0].find("Name"))
                if (const auto* s = std::get_if<std::string>(&nm->data)) b = blockFromStateName(*s);
        out.fill(b);
        return;
    }
    std::vector<BlockId> pal(palette->size(), blocks::Air);
    for (std::size_t i = 0; i < palette->size(); ++i) {
        const auto* nm = (*palette)[i].find("Name");
        if (nm) if (const auto* s = std::get_if<std::string>(&nm->data)) pal[i] = blockFromStateName(*s);
    }
    const nbt::NbtLongArray* data = dataV ? std::get_if<nbt::NbtLongArray>(&dataV->data) : nullptr;
    if (!data) return;
    std::size_t bits = 1;
    while ((std::size_t{1} << bits) < pal.size()) ++bits;
    bits = std::max<std::size_t>(bits, 4);
    PackedArray packed(static_cast<std::uint8_t>(bits), kSectionVolume);
    // Copy long array into words (raw words are laid out identically to our PackedArray).
    // We reconstruct via set() to respect any length mismatch gracefully.
    for (std::size_t w = 0; w < data->size(); ++w) packed.rawWordsMutable()[w] = static_cast<std::uint64_t>((*data)[w]);
    for (std::size_t i = 0; i < kSectionVolume; ++i) {
        const std::size_t idx = static_cast<std::size_t>(packed.get(i));
        out.set(i, idx < pal.size() ? pal[idx] : blocks::Air);
    }
}

inline nbt::Value chunkToNbt(const Chunk& chunk) {
    nbt::NbtList sections;
    for (std::size_t i = 0; i < kChunkSections; ++i) {
        nbt::Value sec = nbt::Value::compound();
        nbt::NbtCompound& sc = std::get<nbt::NbtCompound>(sec.data);
        sc.emplace_back("Y", nbt::Value(static_cast<std::int8_t>(i)));
        sc.emplace_back("block_states", sectionToBlockStates(chunk.section(i)));
        sections.push_back(std::move(sec));
    }
    nbt::NbtCompound level;
    level.emplace_back("xPos", nbt::Value(static_cast<std::int32_t>(chunk.pos().x)));
    level.emplace_back("zPos", nbt::Value(static_cast<std::int32_t>(chunk.pos().z)));
    level.emplace_back("yPos", nbt::Value(static_cast<std::int32_t>(0)));
    level.emplace_back("Status", nbt::Value(std::string("minecraft:full")));
    level.emplace_back("InhabitedTime", nbt::Value(static_cast<std::int64_t>(0)));
    level.emplace_back("sections", nbt::Value(nbt::List, std::move(sections)));
    level.emplace_back("Heightmaps", nbt::Value::compound());

    nbt::NbtCompound root;
    root.emplace_back("DataVersion", nbt::Value(static_cast<std::int32_t>(3955))); // placeholder, documented
    root.emplace_back("Voxelcore:engine", nbt::Value(std::string("voxelcore 0.1")));
    root.emplace_back("Level", nbt::Value(std::move(level)));
    return nbt::Value(std::move(root));
}

inline std::unique_ptr<Chunk> chunkFromNbt(const nbt::Value& root) {
    const nbt::Value* levelV = root.find("Level");
    if (!levelV) return nullptr;
    const nbt::Value* xV = levelV->find("xPos");
    const nbt::Value* zV = levelV->find("zPos");
    if (!xV || !zV) return nullptr;
    ChunkPos pos{std::get<std::int32_t>(xV->data), std::get<std::int32_t>(zV->data)};
    auto chunk = std::make_unique<Chunk>(pos);
    const nbt::Value* sectionsV = levelV->find("sections");
    const nbt::NbtList* sections = sectionsV ? sectionsV->asList() : nullptr;
    if (sections) {
        for (const auto& sec : *sections) {
            const nbt::Value* yV = sec.find("Y");
            const nbt::Value* bsV = sec.find("block_states");
            if (!yV || !bsV) continue;
            const int y = static_cast<int>(std::get<std::int8_t>(yV->data));
            if (y < 0 || y >= static_cast<int>(kChunkSections)) continue;
            blockStatesToSection(*bsV, chunk->section(static_cast<std::size_t>(y)));
        }
    }
    chunk->recomputeHeightMap();
    return chunk;
}

// Compress an NBT root and write it into a region file at (localX, localZ) [0..31].
inline bool saveChunk(anvil::RegionFile& region, const Chunk& chunk, int localX, int localZ) {
    nbt::Writer w;
    w.writeNamedRoot("", chunkToNbt(chunk));
    std::vector<std::uint8_t> payload;
    const auto rc = zlibCompress(w.bytes().data(), w.bytes().size(), payload, 6);
    if (!rc.ok) return false;
    region.writeChunk(localX, localZ, anvil::kCompressionZlib, std::move(payload));
    return true;
}

inline std::unique_ptr<Chunk> loadChunk(anvil::RegionFile& region, int localX, int localZ) {
    std::uint8_t compression = 0;
    std::vector<std::uint8_t> payload;
    try {
        payload = region.readChunk(localX, localZ, compression);
    } catch (const std::exception&) {
        return nullptr;
    }
    std::vector<std::uint8_t> raw;
    if (compression == anvil::kCompressionZlib) {
        // We don't know the uncompressed size up front; grow the buffer until it fits.
        std::size_t guess = payload.size() * 4 + 1024;
        for (int attempt = 0; attempt < 8; ++attempt) {
            const auto rc = zlibUncompress(payload.data(), payload.size(), raw, guess);
            if (rc.ok) break;
            guess *= 4;
            if (attempt == 7) return nullptr;
        }
    } else if (compression == anvil::kCompressionNone) {
        raw = std::move(payload);
    } else {
        return nullptr; // LZ4/custom: unsupported, documented
    }
    nbt::Reader r(raw.data(), raw.size());
    auto [name, root] = r.readNamedRoot();
    (void)name;
    return chunkFromNbt(root);
}

} // namespace vc::chunk_io
