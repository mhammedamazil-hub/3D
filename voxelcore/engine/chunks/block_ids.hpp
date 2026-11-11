// PROJECT VOXELCORE — minimal block registry (Minecraft-compatible ids can be mapped here).
#pragma once
#include "../core/types.hpp"

namespace vc::blocks {
inline constexpr BlockId Air       = 0;
inline constexpr BlockId Stone     = 1;
inline constexpr BlockId Dirt      = 2;
inline constexpr BlockId Grass     = 3;
inline constexpr BlockId Sand      = 4;
inline constexpr BlockId Water     = 5;
inline constexpr BlockId Log       = 6;
inline constexpr BlockId Leaves    = 7;
inline constexpr BlockId Bedrock   = 8;
inline constexpr BlockId Snow      = 9;
inline constexpr BlockId Count     = 10;

// Whether a block fully occludes the face of a neighbour (drives visible-face elimination).
constexpr bool opaque(BlockId b) {
    switch (b) {
        case Air: case Water: case Leaves: return false;
        default: return true;
    }
}
// Whether a block is transparent but still renders (cutout/translucent).
constexpr bool renders(BlockId b) { return b != Air; }
constexpr bool cutout(BlockId b) { return b == Leaves; }
constexpr bool translucent(BlockId b) { return b == Water; }

// Face material tag → later mapped to texture indices per material system (stage 9).
constexpr const char* name(BlockId b) {
    switch (b) {
        case Air: return "air"; case Stone: return "stone"; case Dirt: return "dirt";
        case Grass: return "grass_block"; case Sand: return "sand"; case Water: return "water";
        case Log: return "oak_log"; case Leaves: return "oak_leaves"; case Bedrock: return "bedrock";
        case Snow: return "snow"; default: return "unknown";
    }
}
} // namespace vc::blocks
