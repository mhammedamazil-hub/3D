#version 450
// PROJECT VOXELCORE — E7 records vertex-pulling shader.
// One instance per 8-byte record; gl_VertexIndex in [0,6) expands the quad.
// Positions are chunk-local; the push constant `origin` adds the chunk's absolute
// origin (unlike the CPU path, where the mesher emits absolute coordinates directly).
// Shading replicates shadeFace() exactly (same float op order, floor instead of the
// CPU's unsigned truncation, which agrees for non-negative products). Keep in sync with
// engine/rendering/mesh_triangles.hpp + face_colors.hpp + mesher.hpp faceSunFactor.
// CI gate: records_parity renders the same scene both ways and requires byte-identical PPM.
layout(std430, set = 0, binding = 0) readonly buffer RecordBuffer { uvec2 records[]; } buf;
layout(push_constant) uniform PushConstants { mat4 mvp; vec4 origin; } pc;
layout(location = 0) out vec4 fragColor;

const float kSun[6] = float[](0.72, 0.72, 1.0, 0.5, 0.8, 0.8);
const vec4 kColor[10] = vec4[](
    vec4(170.0, 51.0, 170.0, 255.0),  // 0 default (magenta, matches faceColor default)
    vec4(136.0, 136.0, 136.0, 255.0), // 1 stone
    vec4(121.0, 85.0, 58.0, 255.0),   // 2 dirt
    vec4(94.0, 156.0, 63.0, 255.0),   // 3 grass
    vec4(214.0, 204.0, 161.0, 255.0), // 4 sand
    vec4(63.0, 111.0, 214.0, 159.0),  // 5 water (0x9F alpha)
    vec4(107.0, 74.0, 43.0, 255.0),   // 6 log
    vec4(47.0, 107.0, 47.0, 255.0),   // 7 leaves
    vec4(51.0, 51.0, 51.0, 255.0),    // 8 bedrock
    vec4(242.0, 245.0, 247.0, 255.0)  // 9 snow
);

void main() {
    uvec2 rec = buf.records[gl_InstanceIndex];
    uint x = rec.x & 0xFu;
    uint z = (rec.x >> 4u) & 0xFu;
    uint y = (rec.x >> 8u) & 0x3Fu;
    uint uE = ((rec.x >> 14u) & 0xFu) + 1u;
    uint vE = ((rec.x >> 18u) & 0xFu) + 1u;
    uint dir = (rec.x >> 22u) & 0x7u;
    uint block = rec.y & 0xFFFFu;
    uint ao[4] = uint[4]((rec.y >> 16u) & 0x3u, (rec.y >> 18u) & 0x3u,
                         (rec.y >> 20u) & 0x3u, (rec.y >> 22u) & 0x3u);
    float lightK = 0.2 + 0.8 * (float((rec.y >> 24u) & 0xFu) / 15.0);

    vec3 c[4];
    if (dir <= 1u) {                       // PosX(0)/NegX(1): plane x = slice + (PosX ? 1 : 0)
        float xp = float(x) + ((dir == 0u) ? 1.0 : 0.0);
        float y0 = float(y), y1 = y0 + float(vE);
        float z0 = float(z), z1 = z0 + float(uE);
        c[0] = vec3(xp, y0, z0); c[1] = vec3(xp, y0, z1); c[2] = vec3(xp, y1, z1); c[3] = vec3(xp, y1, z0);
    } else if (dir <= 3u) {                // PosY(2)/NegY(3): plane y = slice + (PosY ? 1 : 0)
        float yp = float(y) + ((dir == 2u) ? 1.0 : 0.0);
        float x0 = float(x), x1 = x0 + float(uE);
        float z0 = float(z), z1 = z0 + float(vE);
        c[0] = vec3(x0, yp, z0); c[1] = vec3(x1, yp, z0); c[2] = vec3(x1, yp, z1); c[3] = vec3(x0, yp, z1);
    } else {                               // PosZ(4)/NegZ(5): plane z = slice + (PosZ ? 1 : 0)
        float zp = float(z) + ((dir == 4u) ? 1.0 : 0.0);
        float x0 = float(x), x1 = x0 + float(uE);
        float y0 = float(y), y1 = y0 + float(vE);
        c[0] = vec3(x0, y0, zp); c[1] = vec3(x1, y0, zp); c[2] = vec3(x1, y1, zp); c[3] = vec3(x0, y1, zp);
    }

    // Winding must match expandQuads(): flip = (NegX || NegY || PosZ).
    const uint stdOrder[6]  = uint[](0u, 1u, 2u, 0u, 2u, 3u);
    const uint flipOrder[6] = uint[](0u, 2u, 1u, 0u, 3u, 2u);
    bool flip = (dir == 1u || dir == 3u || dir == 4u);
    uint corner = flip ? flipOrder[gl_VertexIndex] : stdOrder[gl_VertexIndex];

    vec3 p = c[corner] + pc.origin.xyz;    // exact for integer coordinates
    float aoK = 0.35 + 0.2167 * float(ao[corner]);
    float k = aoK * lightK * kSun[dir];    // same op order as shadeFace (non-negative => floor == trunc)
    vec4 raw = (block <= 9u) ? kColor[block] : kColor[0];
    vec3 shaded = floor(raw.rgb * k);
    fragColor = vec4(shaded / 255.0, raw.a / 255.0);
    gl_Position = pc.mvp * vec4(p, 1.0);
}
