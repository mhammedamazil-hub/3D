# Desktop platform (stage 4/13)

Planned: Vulkan 1.2 windowed/fullscreen app (GLFW or SDL3 — decision pending,
see ADR-002), X11/Wayland, frame pacing, HDR path. The engine core builds and runs
headless today (`tools/voxelcore-cli`); the desktop app lands with the Vulkan backend.
