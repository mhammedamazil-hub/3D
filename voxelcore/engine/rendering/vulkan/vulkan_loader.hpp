// PROJECT VOXELCORE — minimal runtime dynamic loader for the Vulkan loader library.
// Rationale (ARCHITECTURE_DECISIONS.md): builds must not depend on a Vulkan loader being
// installed (Android loads libvulkan.so the same way), so every vk* symbol is resolved via
// dlopen + vkGetInstanceProcAddr/vkGetDeviceProcAddr at runtime. If resolution fails the
// caller treats it as "no Vulkan available" and degrades cleanly instead of failing to build.
#pragma once

#include <vulkan/vulkan.h>
#include <dlfcn.h>
#include <string>
#include <vector>
#include <cstdio>

namespace vc::vk {

struct VulkanLoadError : std::runtime_error { using std::runtime_error::runtime_error; };

struct VulkanAPI {
    void* lib = nullptr;
    PFN_vkGetInstanceProcAddr getInstanceProcAddr = nullptr;
    PFN_vkGetDeviceProcAddr getDeviceProcAddr = nullptr;

// clang-format off
#define VC_VK_GLOBAL_FUNCTIONS(X) \
    X(CreateInstance)

#define VC_VK_INSTANCE_FUNCTIONS(X) \
    X(DestroyInstance) \
    X(EnumeratePhysicalDevices) \
    X(GetPhysicalDeviceProperties) \
    X(GetPhysicalDeviceQueueFamilyProperties) \
    X(GetPhysicalDeviceMemoryProperties) \
    X(CreateDevice) \
    X(GetDeviceProcAddr)

#define VC_VK_DEVICE_FUNCTIONS(X) \
    X(DestroyDevice) \
    X(DeviceWaitIdle) \
    X(GetDeviceQueue) \
    X(CreateCommandPool) \
    X(DestroyCommandPool) \
    X(AllocateCommandBuffers) \
    X(FreeCommandBuffers) \
    X(ResetCommandBuffer) \
    X(BeginCommandBuffer) \
    X(EndCommandBuffer) \
    X(CreateFence) \
    X(DestroyFence) \
    X(WaitForFences) \
    X(ResetFences) \
    X(CreateBuffer) \
    X(DestroyBuffer) \
    X(GetBufferMemoryRequirements) \
    X(BindBufferMemory) \
    X(AllocateMemory) \
    X(FreeMemory) \
    X(MapMemory) \
    X(UnmapMemory) \
    X(CreateImage) \
    X(DestroyImage) \
    X(GetImageMemoryRequirements) \
    X(BindImageMemory) \
    X(CreateImageView) \
    X(DestroyImageView) \
    X(CreateRenderPass) \
    X(DestroyRenderPass) \
    X(CreateFramebuffer) \
    X(DestroyFramebuffer) \
    X(CreateShaderModule) \
    X(DestroyShaderModule) \
    X(CreatePipelineLayout) \
    X(DestroyPipelineLayout) \
    X(CreateGraphicsPipelines) \
    X(DestroyPipeline) \
    X(QueueSubmit) \
    X(CmdBeginRenderPass) \
    X(CmdEndRenderPass) \
    X(CmdBindPipeline) \
    X(CmdBindVertexBuffers) \
    X(CmdBindIndexBuffer) \
    X(CmdPushConstants) \
    X(CmdDrawIndexed) \
    X(CmdCopyImageToBuffer)
// clang-format on

#define VC_VK_DECLARE_FN(Name) PFN_vk##Name Name = nullptr;
    VC_VK_GLOBAL_FUNCTIONS(VC_VK_DECLARE_FN)
    VC_VK_INSTANCE_FUNCTIONS(VC_VK_DECLARE_FN)
    VC_VK_DEVICE_FUNCTIONS(VC_VK_DECLARE_FN)
#undef VC_VK_DECLARE_FN

    bool loadLibrary() {
        if (lib) return true;
        for (const char* candidate : {"libvulkan.so.1", "libvulkan.so", "libvulkan.dylib", "vulkan-1.dll"}) {
            lib = dlopen(candidate, RTLD_NOW | RTLD_LOCAL);
            if (lib) { std::fprintf(stderr, "vulkan: loaded %s\n", candidate); return true; }
        }
        return false;
    }

    void require(void* fn, const char* name) const {
        if (!fn) throw VulkanLoadError(std::string("Vulkan loader is missing symbol: ") + name);
    }

    // Stage 1: global functions (resolvable with a NULL instance).
    void loadPreInstance() {
        if (!loadLibrary()) throw VulkanLoadError("libvulkan not found (install libvulkan1 / Vulkan SDK)");
        getInstanceProcAddr = reinterpret_cast<PFN_vkGetInstanceProcAddr>(dlsym(lib, "vkGetInstanceProcAddr"));
        require(reinterpret_cast<void*>(getInstanceProcAddr), "vkGetInstanceProcAddr");
#define VC_VK_LOAD_GLOBAL(Name) \
        Name = reinterpret_cast<PFN_vk##Name>(getInstanceProcAddr(nullptr, "vk" #Name)); \
        require(reinterpret_cast<void*>(Name), "vk" #Name);
        VC_VK_GLOBAL_FUNCTIONS(VC_VK_LOAD_GLOBAL)
#undef VC_VK_LOAD_GLOBAL
    }

    // Stage 2: instance-level functions (everything called before device creation).
    void loadInstance(VkInstance instance) {
#define VC_VK_LOAD_INSTANCE(Name) \
        Name = reinterpret_cast<PFN_vk##Name>(getInstanceProcAddr(instance, "vk" #Name)); \
        require(reinterpret_cast<void*>(Name), "vk" #Name);
        VC_VK_INSTANCE_FUNCTIONS(VC_VK_LOAD_INSTANCE)
#undef VC_VK_LOAD_INSTANCE
    }

    // Stage 3: device-level functions.
    void loadDevice(VkDevice device, VkInstance instance) {
        getDeviceProcAddr = reinterpret_cast<PFN_vkGetDeviceProcAddr>(getInstanceProcAddr(instance, "vkGetDeviceProcAddr"));
        require(reinterpret_cast<void*>(getDeviceProcAddr), "vkGetDeviceProcAddr");
        // GetDeviceProcAddr itself is loaded in stage 2; keep a consistent copy here.
        (void)instance;
#define VC_VK_LOAD_DEVICE(Name) \
        Name = reinterpret_cast<PFN_vk##Name>(getDeviceProcAddr(device, "vk" #Name)); \
        require(reinterpret_cast<void*>(Name), "vk" #Name);
        VC_VK_DEVICE_FUNCTIONS(VC_VK_LOAD_DEVICE)
#undef VC_VK_LOAD_DEVICE
    }

    void unload() {
        if (lib) dlclose(lib);
        lib = nullptr;
        getInstanceProcAddr = nullptr;
        getDeviceProcAddr = nullptr;
    }
    ~VulkanAPI() { unload(); }
};

} // namespace vc::vk
