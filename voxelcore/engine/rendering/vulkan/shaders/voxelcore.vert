#version 450
layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec4 inColor;
layout(push_constant) uniform PushConstants { mat4 mvp; } pc;
layout(location = 0) out vec4 fragColor;
// Force bitwise-identical gl_Position across passes (multi-pass invariance): the E7
// records pipeline rasterizes the same triangles computed from the same floats; without
// this, sub-ULP codegen differences flip coverage on hairline slivers.
invariant gl_Position;
void main() {
    vec4 p4 = vec4(inPosition, 1.0);
    // Explicit FMA chain: bitwise-identical gl_Position across shaders and backends
    // (IEEE fma is exactly rounded; compiler contraction cannot diverge).
    gl_Position = vec4(
        fma(pc.mvp[0][0], p4.x, fma(pc.mvp[1][0], p4.y, fma(pc.mvp[2][0], p4.z, pc.mvp[3][0] * p4.w))),
        fma(pc.mvp[0][1], p4.x, fma(pc.mvp[1][1], p4.y, fma(pc.mvp[2][1], p4.z, pc.mvp[3][1] * p4.w))),
        fma(pc.mvp[0][2], p4.x, fma(pc.mvp[1][2], p4.y, fma(pc.mvp[2][2], p4.z, pc.mvp[3][2] * p4.w))),
        fma(pc.mvp[0][3], p4.x, fma(pc.mvp[1][3], p4.y, fma(pc.mvp[2][3], p4.z, pc.mvp[3][3] * p4.w))));
    fragColor = inColor;
}
