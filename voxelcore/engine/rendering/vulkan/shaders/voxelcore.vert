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
    gl_Position = pc.mvp * vec4(inPosition, 1.0);
    fragColor = inColor;
}
