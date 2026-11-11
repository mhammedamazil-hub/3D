# Android platform (stage 12)

Planned: NativeActivity-based app, NDK + CMake toolchain, OpenGL ES 3.2 fallback and
Vulkan 1.1+ path with capability detection, APK assets, touch input, lifecycle
suspend/resume, thermal-quality tiering. CI currently compile-checks the engine for
arm64-v8a on every push (see `.github/workflows/ci.yml`); nothing is claim-runnable yet.
